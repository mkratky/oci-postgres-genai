# Import
import oci
import os
import json 
import time
import pathlib
import requests

from datetime import datetime
from base64 import b64decode

# Constant
LOG_DIR = '/tmp/app_log'
UNIQUE_ID = "ID"

# Function
def log(s):
   print( s, flush=True)

def get_cursor_by_group(sc, sid, group_name, instance_name):
    print(" Creating a cursor for group {}, instance {}".format(group_name, instance_name))
    cursor_details = oci.streaming.models.CreateGroupCursorDetails(group_name=group_name, instance_name=instance_name,
                                                                   type=oci.streaming.models.
                                                                   CreateGroupCursorDetails.TYPE_TRIM_HORIZON,
                                                                   commit_on_get=True)
    response = sc.create_group_cursor(sid, cursor_details)
    return response.data.value

def log_in_file(prefix, value):
    global UNIQUE_ID
    filename = prefix+"_"+UNIQUE_ID+".txt"
    with open(LOG_DIR+"/"+filename, "w") as text_file:
        text_file.write(value)
    log("log file: " + filename )    

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
                if message.key is None:
                    key = "Null"
                else:
                    key = b64decode(message.key.encode()).decode()
                json_value = b64decode(message.value.encode()).decode(); 
                log("{}: {}".format(key,json_value))
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

def eventDocument(value):
    global UNIQUE_ID 
    UNIQUE_ID = datetime.now().strftime("%Y%m%d-%H%M%S.%f")

    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    # ex: /n/fr03kzmuvhtf/b/psql-public-bucket/o/country.pdf"
    # XXX OIC: resourcePath
    resourceId = value["data"]["resourceId"]
    log( eventType + " - " + resourceId ) 

    if eventType in ["com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject"]:
        insertDocument( value )
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        deleteDocument( value )

def insertDocument(value):
    resourceName = value["data"]["resourceName"]
    lowerResourceName = resourceName.lower()
    resourceExtension = pathlib.Path(lowerResourceName).suffix
    log( "Extension:" + resourceExtension )
     
    # Content 
    result = { "content": "-" }
    if resourceName.startswith("belgian"):
      log('BELGIAN TODO')
    elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
      log('IMAGE TODO')
    elif resourceExtension in [".json"]:
      log('JSON TODO')
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
      log('VOICE TODO')
    elif resourceExtension in [".tif"]:
      # This will create a JSON file in Object Storage that will create a second even with resourceExtension "json" 
      documentUnderstanding(value)
      return
    elif resourceName.endswith("/"):
      # Ignore
      return
    else:
      result = invokeTika(value)
    var_content_1 = result.content
    log_in_file("content", result.content)

    # Summary 
    summary = "-"
    if len(result.content)>250:
        summarizeContent(value, result.content)
    
    # Delete Document in repository
    if value["eventType"] == "com.oraclecloud.objectstorage.updateobject":
        deleteDocument( value )


def invokeTika(value):
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
    log( "Tika response: " + resp.data.text)
    j = json.loads(resp.data.text)

    result = {
        "resourceName": j["resourceName"],
        "date": UNIQUE_ID,
        "applicationName": j["Application-Name"],
        "modified": UNIQUE_ID,
        "contentType": j["Content-Type"],
        "parsedBy": j["X-Parsed-By"],
        "creationDate": UNIQUE_ID,
        "author": j["Author"],
        "publisher": j["publisher"],
        "content": j["content"],
        "path": resourceId
    }
    return result

def deleteDocument(value):
    print ('TODO')

def summarizeContent(value,content):
    global signer
    compartmentId = value["data"]["compartmentId"]
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com'
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
    response = requests.post(endpoint, json=body, auth=signer)
    response.raise_for_status()
    log(response)    
    log(response.json()['id'])    

def documentUnderstanding(value):
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
    log(resp)

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
group_cursor = get_cursor_by_group(stream_client, ociStreamOcid, "app-group", "app-instance-1")
stream_loop(stream_client, ociStreamOcid, group_cursor)
