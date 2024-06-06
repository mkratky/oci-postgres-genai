# Import
import oci
import os
import json 
import time
import pathlib
import requests
import pprint
import psycopg2

from psycopg2.extras import execute_values
from datetime import datetime
from base64 import b64decode

# Constant
LOG_DIR = '/tmp/app_log'
UNIQUE_ID = "ID"

# Connection
dbConn = None

## -- log ------------------------------------------------------------------

def log(s):
   print( s, flush=True)

## -- dictValue ------------------------------------------------------------

def dictValue(d,key):
   value = d.get(key)
   if value is None:
       return "-"
   else:
       return value

## -- cutInChunks -----------------------------------------------------------

def cutInChunks(text):
    result = []
    prev = ""
    i = 0
    last_good_separator = 0
    last_medium_separator = 0
    last_bad_separator = 0
    maxlen = 250
    chunck_start = 0
    chunck_end = 0

    for char in text:
        i += 1
        cur = char
        cur2 = prev + cur
        prev = cur

        if cur2 in [ ". ", ".[" , ".\n", "\n\n" ]:
            last_good_separator = i
        if cur in [ "\n" ]:          
            last_medium_separator = i
        if cur in [ " " ]:          
            last_bad_separator = i
        # log( 'cur=' + cur + ' / cur2=' + cur2 )
        if i-chunck_start>maxlen:
            chunck_end = i
            if last_good_separator > 0:
               chunck_end = last_good_separator
            elif last_medium_separator > 0:
               chunck_end = last_medium_separator
            elif last_bad_separator > 0:
               chunck_end = last_bad_separator
            chunck = text[chunck_start:chunck_end]
            log("chunck_start= " + str(chunck_start) + " - " + chunck)   
            result.append( chunck )
            chunck_start=chunck_end 
            last_good_separator = 0
            last_medium_separator = 0
            last_bad_separator = 0
    # Last chunck
    chunck = text[chunck_start:]
    log("chunck_start= " + str(chunck_start) + " - " + chunck)  
    result.append( chunck )
    return result

## -- stream_cursor --------------------------------------------------------

def stream_cursor(sc, sid, group_name, instance_name):
    print(" Creating a cursor for group {}, instance {}".format(group_name, instance_name))
    cursor_details = oci.streaming.models.CreateGroupCursorDetails(group_name=group_name, instance_name=instance_name,
                                                                   type=oci.streaming.models.
                                                                   CreateGroupCursorDetails.TYPE_TRIM_HORIZON,
                                                                   commit_on_get=True)
    response = sc.create_group_cursor(sid, cursor_details)
    return response.data.value

## -- log_in_file --------------------------------------------------------

def log_in_file(prefix, value):
    global UNIQUE_ID
    filename = LOG_DIR+"/"+prefix+"_"+UNIQUE_ID+".txt"
    with open(filename, "w") as text_file:
        text_file.write(value)
    log("log file: " +filename )    

## -- stream_loop --------------------------------------------------------

def stream_loop(client, stream_id, initial_cursor):
    global UNIQUE_ID 
    cursor = initial_cursor
    initDbConn()
    while True:
        get_response = client.get_messages(stream_id, cursor, limit=10)
        # No messages to process. return.
        if not get_response.data:
            return

        # Process the messages
        log(" Read {} messages".format(len(get_response.data)))
        for message in get_response.data:
            try:
                log("--------------------------------------------------------------" )
                if message.key is None:
                    key = "Null"
                else:
                    key = b64decode(message.key.encode()).decode()
                json_value = b64decode(message.value.encode()).decode(); 
                log(json_value)
                UNIQUE_ID = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
                log_in_file("stream", json_value)
                value = json.loads(json_value)
                eventDocument(value)
            except:
                log("Exception: stream_loop") 
                log("key=" + message.key)
                log("value=" + message.value)
            
        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]



## -- eventDocument --------------------------------------------------------

def eventDocument(value):
    global UNIQUE_ID 
    eventType = value["eventType"]
    # ex: /n/fr03kzmuvhtf/b/psql-public-bucket/o/country.pdf"
    # XXX OIC: resourcePath
    resourceId = value["data"]["resourceId"]
    log( "eventType=" + eventType + " - " + resourceId ) 

    if eventType in ["com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject"]:
        insertDocument( value )
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        deleteDocument( value )

## -- insertDocument --------------------------------------------------------

def insertDocument(value):
    resourceName = value["data"]["resourceName"]
    lowerResourceName = resourceName.lower()
    resourceExtension = pathlib.Path(lowerResourceName).suffix
    log( "Extension:" + resourceExtension )
     
    # Content 
    result = { "content": "-" }
    if resourceName.startswith("belgian"):
        result = belgian(value)
    elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
        result = vision(value)
    elif resourceExtension in [".srt"]:
        log("IGNORE .srt")
        return
    elif resourceExtension in [".json"]:
        result = decodeJson(value)
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
        # This will create a SRT file in Object Storage that will create a second even with resourceExtension ".srt" 
        speech(value)
        return
    elif resourceExtension in [".tif"]:
        # This will create a JSON file in Object Storage that will create a second even with resourceExtension "json" 
        documentUnderstanding(value)
        return
    elif resourceName.endswith("/"):
        # Ignore
        return
    else:
        result = invokeTika(value)

    log_in_file("content", result["content"])
    if len(result["content"])==0:
       return 

    # Summary 
    summary = "-"
    if len(result["content"])>250:
        summary = summarizeContent(value, result["content"])
    
    # Delete Document in repository
    if value["eventType"] == "com.oraclecloud.objectstorage.updateobject":
        deleteDocument( value )

    # If no page, just add the content
    if result.get("pages") == None:
        result["pages"] = [ result["content"] ]
            
    for p in result["pages"]:
        # Get Next Chunks
        chuncks = cutInChunks( p )
        for c in chuncks:
            result["cohereEmbed"] = embedText(c)
            insertDb(result)
                
## -- deleteDocument --------------------------------------------------------

def deleteDocument(value):
    log( "<deleteDocument>")
    resourceId = value["data"]["resourceId"]
    deleteDb(resourceId)
    log( "</deleteDocument>")


## -- decodeJson ------------------------------------------------------------------

def decodeJson(value):
    log( "<decodeJson>")
    global signer
    global UNIQUE_ID 
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    # Read the JSON file from the object storage
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
    file_name = LOG_DIR+"/"+UNIQUE_ID+".json"
    with open(file_name, 'wb') as f:
        for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)

    with open(file_name, 'r') as f:
        file_content = f.read()
    log("Read file from object storage: "+ file_name)
    j = json.loads(file_content)   

    if resourceName[:resourceName.index("/")] == "document":
        # DocUnderstanding
        concat_text = ""
        pages = []
        for p in j.get("pages"):
            page = ""
            for l in p.get("lines"):
                page += l.get("text") + "\n"
            pages.append(page)
            concat_text += page + " "    
        original_resourcename = resourceName[:resourceName.index(".json")][resourceName.index("/results/"):]
        result = {
            "resourceName": original_resourcename,
            "date": UNIQUE_ID,
            "applicationName": "OCI Document Understanding",
            "modified": UNIQUE_ID,
            "contentType": j["documentMetadata"]["mimeType"],
            "creationDate": UNIQUE_ID,
            "content": concat_text,
            "pages": pages,
            "path": resourceId
        }
    else:
        # Speech
        original_resourcename = "/n/" + namespace + "/b/" + bucketName + "/o/" + resourceName[:resourceName.index(".json")][resourceName.index("_"):]
        result = {
            "resourceName": original_resourcename,
            "date": UNIQUE_ID,
            "applicationName": "OCI Speech",
            "modified": UNIQUE_ID,
            "contentType": j["audioFormatDetails"]["format"],
            "creationDate": UNIQUE_ID,
            "content": j["transcriptions"][0]["transcription"],
            "path": resourceId
        }
    log( "</decodeJson>")
    return result

## -- invokeTika ------------------------------------------------------------------

def invokeTika(value):
    log( "<invokeTika>")
    global signer
    global UNIQUE_ID 
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    invoke_client = oci.functions.FunctionsInvokeClient(config = {}, service_endpoint=fnInvokeEndpoint, signer=signer)
    # {"bucketName": "xxx", "namespace": "xxx", "resourceName": "xxx"}
    req = '{"bucketName": "' + bucketName + '", "namespace": "' + namespace + '", "resourceName": "' + resourceName + '"}'
    log( "Tika request: " + req)
    resp = invoke_client.invoke_function(fnOcid, invoke_function_body=req)
    log_in_file("tika_resp", resp.data.text) 
    j = json.loads(resp.data.text)
    result = {
        "resourceName": resourceId,
        "date": UNIQUE_ID,
        "applicationName": "Tika Parser",
        "modified": UNIQUE_ID,
        "contentType": dictValue(j,"Content-Type"),
        "parsedBy": dictValue(j,"X-Parsed-By"),
        "creationDate": UNIQUE_ID,
        "author": dictValue(j,"Author"),
        "publisher": dictValue(j,"publisher"),
        "content": j["content"],
        "path": resourceId
    }
    log( "</invokeTika>")
    return result

## -- summarizeContent ------------------------------------------------------

def summarizeContent(value,content):
    log( "<summarizeContent>")
    global signer
    compartmentId = value["data"]["compartmentId"]
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/summarizeText'
    body = {
        "input" : content,
        "servingMode" : {
            "modelId" : "cohere.command",
            "servingType" : "ON_DEMAND"
        },
        "temperature" : 1,
        "length" : "AUTO",
        "extractiveness" : "AUTO",
        "format" : "AUTO",
        "additionalCommand" : "",
        "compartmentId" : compartmentId
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)   
    log_in_file("summarizeContent_resp",str(resp.content)) 
    j = json.loads(resp.content)   
    log( "</summarizeContent>")
    return dictValue(j,"summary") 

## -- embedText ------------------------------------------------------

#XXXXX Ideally all vector should be created in one call
def embedText(c):
    log( "<embedText>")
    global signer
    compartmentId = os.getEnv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/embedText'
    body = {
        "inputs" : [ c ],
        "servingMode" : {
            "servingType" : "ON_DEMAND",
            "modelId" : "cohere.embed-english-light-v2.0"
        },
        "truncate" : "START",
        "compartmentId" : compartmentId
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("embedText_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    log( "</embedText>")
    return dictValue(j,"embeddings")[0] 


## -- vision --------------------------------------------------------------

def vision(value):
    log( "<vision>")
    global UNIQUE_ID 
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log_in_file("vision_resp", str(resp.data)) 

    concat_imageText = ""
    for l in resp.data.image_text.lines:
      concat_imageText += l.text + " "
    log("concat_imageText: " + concat_imageText )

    concat_labels = ""
    for l in resp.data.labels:
      concat_labels += l.name + " "
    log("concat_labels: " +concat_labels )

    result = {
        "resourceName": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "Image",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": concat_imageText + " " + concat_labels,
        "path": resourceId,
        "other1": concat_labels
    }
    log( "</vision>")
    return result    

## -- belgian --------------------------------------------------------------

def belgian(value):
    log( "<belgian>")
    global UNIQUE_ID 
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log(resp.data)
    # log(json.dumps(resp,sort_keys=True, indent=4))

    name = resp.data.image_text.lines[8]
    id = resp.data.image_text.lines[19]
    birthdate = resp.data.image_text.lines[22]

    result = {
        "resourceName": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "Belgian ID",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": "Belgian identity card. Name="+name,
        "path": resourceId,
        "other1": id,
        "other2": birthdate,
    }
    log( "</belgian>")
    return result  

## -- speech --------------------------------------------------------------

def speech(value):
    log( "<speech>")
    global UNIQUE_ID 
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]

    speech_client = oci.ai_speech.AIServiceSpeechClient(config = {}, signer=signer)
    job = {
        "normalization": {
                "isPunctuationEnabled": True
        },
        "compartmentId": compartmentId,
        "displayName": UNIQUE_ID,
        "modelDetails": {
                "domain": "GENERIC",
                "languageCode": "en-US"
        },
        "inputLocation": {
                "locationType": "OBJECT_LIST_INLINE_INPUT_LOCATION",
                "objectLocations": [
                    {
                            "namespaceName": namespace,
                            "bucketName": bucketName,
                            "objectNames": [
                                resourceName
                            ]
                    }
                ]
        },
        "outputLocation": {
                "namespaceName": namespace,
                "bucketName": bucketName,
                "prefix": "speech"
        },
        "additionalTranscriptionFormats": [
                "SRT"
        ]
    }
    resp = speech_client.create_transcription_job(job)
    log_in_file("speech_resp",str(resp.data))
    log( "</speech>")

## -- documentUnderstanding -------------------------------------------------

def documentUnderstanding(value):
    log( "<documentUnderstanding>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]

    document_understanding_client = oci.ai_document.AIServiceDocumentClient(config = {}, signer=signer)
    job = {
        "processorConfig": {
            "language": "ENG",
            "processorType": "GENERAL",
            "features": [
                {
                    "featureType": "TEXT_EXTRACTION"
                }
            ],
            "isZipOutputEnabled": False
        },
        "compartmentId": compartmentId,
        "inputLocation": {
            "sourceType": "OBJECT_STORAGE_LOCATIONS",
            "objectLocations": [
                {
                    "bucketName": bucketName,
                    "namespaceName": namespace,
                    "objectName": resourceName
                }
            ]
        },
        "outputLocation": {
            "namespaceName": namespace,
            "bucketName": bucketName,
            "prefix": "document"
        }
    }
    resp = document_understanding_client.create_processor_job(job)
    log_in_file("documentUnderstanding_resp",str(resp.data))
    log( "</documentUnderstanding>")

## -- initDbConn --------------------------------------------------------------

def initDbConn():
    global dbConn 
    dbConn = psycopg2.connect(dbname="postgres", user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_URL'))
    dbConn.autocommit = True

## -- closeDbConn --------------------------------------------------------------

def closeDbConn():
    global dbConn 
    dbConn.close()

# -- insertDb -----------------------------------------------------------------

def insertDb(result):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO oic (
            application_name, author, translation, cohere_embed, content, content_type,
            creation_date, date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, context
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    data = [
        (dictValue(result,"applicationName"), 
            dictValue(result,"author"),
            dictValue(result,"translation"),
            dictValue(result,"cohereEmbed"),
            dictValue(result,"content"),
            dictValue(result,"contentType"),
            dictValue(result,"creationDate"),
            dictValue(result,"date"),
            dictValue(result,"modified"),
            dictValue(result,"other1"),
            dictValue(result,"other2"),
            dictValue(result,"other3"),
            dictValue(result,"parsed_by"),
            dictValue(result,"filename"),
            dictValue(result,"path"),
            dictValue(result,"publisher"),
            dictValue(result,"region"),
            dictValue(result,"context")
        )
    ]
    try:
        cur.executemany(stmt, data)
        print(f"Successfully inserted {cur.rowcount} records.")
    except (Exception, psycopg2.Error) as error:
        print(f"Error inserting records: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- deleteDb -----------------------------------------------------------------

def deleteDb(path):  
    global dbConn
    cur = dbConn.cursor()
    stmt = "delete from oic where path=%s"
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDb> Successfully deleted")
    except (Exception, psycopg2.Error) as error:
        print(f"<deleteDb> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

## -- main ------------------------------------------------------------------

# Create Log directory
if os.path.isdir(LOG_DIR) == False:
    os.mkdir(LOG_DIR) 

# get signer from instance principals token
ociMessageEndpoint = os.getenv('STREAM_MESSAGE_ENDPOINT')
ociStreamOcid = os.getenv('STREAM_OCID')

# Instance Principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}
# stream_client = oci.streaming.StreamClient(config, service_endpoint=ociMessageEndpoint)
stream_client = oci.streaming.StreamClient(config = {}, service_endpoint=ociMessageEndpoint, signer=signer)

# A cursor can be created as part of a consumer group.
# Committed offsets are managed for the group, and partitions
# are dynamically balanced amongst consumers in the group.
initDbConn()
group_cursor = stream_cursor(stream_client, ociStreamOcid, "app-group", "app-instance-1")
stream_loop(stream_client, ociStreamOcid, group_cursor)
closeDbConn()
