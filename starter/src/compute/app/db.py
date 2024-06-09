# Import
import oci
import os
import json 
import time
import pathlib
import requests
import psycopg2
import traceback
import search_shared
from search_shared import log
from search_shared import log_in_file
from search_shared import dictString

from psycopg2.extras import execute_values
from datetime import datetime
from base64 import b64decode

from base64 import b64decode

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

## -- stream_loop --------------------------------------------------------

def stream_loop(client, stream_id, initial_cursor):
    cursor = initial_cursor
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
                search_shared.UNIQUE_ID = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
                log_in_file("stream", json_value)
                value = json.loads(json_value)
                eventDocument(value)
            except:
                log("Exception: stream_loop") 
                print(traceback.format_exc())
            
        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]



## -- eventDocument --------------------------------------------------------

def eventDocument(value):
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
            result["cohereEmbed"] = search_shared.embedText(c,signer)
            search_shared.insertDb(result,c)
                
## -- deleteDocument --------------------------------------------------------

def deleteDocument(value):
    log( "<deleteDocument>")
    resourceId = value["data"]["resourceId"]
    search_shared.deleteDb(resourceId)
    log( "</deleteDocument>")


## -- decodeJson ------------------------------------------------------------------

def decodeJson(value):
    log( "<decodeJson>")
    global signer
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    # Read the JSON file from the object storage
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
    file_name = search_shared.LOG_DIR+"/"+search_shared.UNIQUE_ID+".json"
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
            "filename": original_resourcename,
            "date": search_shared.UNIQUE_ID,
            "applicationName": "OCI Document Understanding",
            "modified": search_shared.UNIQUE_ID,
            "contentType": j["documentMetadata"]["mimeType"],
            "creationDate": search_shared.UNIQUE_ID,
            "content": concat_text,
            "pages": pages,
            "path": resourceId
        }
    else:
        # Speech
        original_resourcename = "/n/" + namespace + "/b/" + bucketName + "/o/" + resourceName[:resourceName.index(".json")][resourceName.index("_"):]
        result = {
            "filename": original_resourcename,
            "date": search_shared.UNIQUE_ID,
            "applicationName": "OCI Speech",
            "modified": search_shared.UNIQUE_ID,
            "contentType": j["audioFormatDetails"]["format"],
            "creationDate": search_shared.UNIQUE_ID,
            "content": j["transcriptions"][0]["transcription"],
            "path": resourceId
        }
    log( "</decodeJson>")
    return result

## -- invokeTika ------------------------------------------------------------------

def invokeTika(value):
    log( "<invokeTika>")
    global signer
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
        "filename": resourceName,
        "date": search_shared.UNIQUE_ID,
        "applicationName": "Tika Parser",
        "modified": search_shared.UNIQUE_ID,
        "contentType": dictString(j,"Content-Type"),
        "parsedBy": dictString(j,"X-Parsed-By"),
        "creationDate": search_shared.UNIQUE_ID,
        "author": dictString(j,"Author"),
        "publisher": dictString(j,"publisher"),
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
    return dictString(j,"summary") 

## -- vision --------------------------------------------------------------

def vision(value):
    log( "<vision>")
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
        "filename": resourceName,
        "date": search_shared.UNIQUE_ID,
        "modified": search_shared.UNIQUE_ID,
        "contentType": "Image",
        "parsedBy": "OCI Vision",
        "creationDate": search_shared.UNIQUE_ID,
        "content": concat_imageText + " " + concat_labels,
        "path": resourceId,
        "other1": concat_labels
    }
    log( "</vision>")
    return result    

## -- belgian --------------------------------------------------------------

def belgian(value):
    log( "<belgian>")
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
        "filename": resourceName,
        "date": search_shared.UNIQUE_ID,
        "modified": search_shared.UNIQUE_ID,
        "contentType": "Belgian ID",
        "parsedBy": "OCI Vision",
        "creationDate": search_shared.UNIQUE_ID,
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
        "displayName": search_shared.UNIQUE_ID,
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

## -- main ------------------------------------------------------------------

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

while True:
    search_shared.initDbConn()
    group_cursor = stream_cursor(stream_client, ociStreamOcid, "app-group", "app-instance-1")
    stream_loop(stream_client, ociStreamOcid, group_cursor)
    search_shared.closeDbConn()
    time.sleep(30)
