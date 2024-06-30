# Import
import oci
import os
import json 
import time
import pathlib
import traceback
import shared_oci
from shared_oci import log
from shared_oci import log_in_file
import shared_db

from datetime import datetime
from base64 import b64decode

## -- stream_cursor --------------------------------------------------------

def stream_cursor(sc, sid, group_name, instance_name):
    log("<stream_cursor>")
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
        log("<stream_loop> Read {} messages".format(len(get_response.data)))
        for message in get_response.data:
            try:
                log("--------------------------------------------------------------" )
                if message.key is None:
                    key = "Null"
                else:
                    key = b64decode(message.key.encode()).decode()
                json_value = b64decode(message.value.encode()).decode(); 
                log(json_value)
                shared_oci.UNIQUE_ID = datetime.now().strftime("%Y%m%d-%H%M%S.%f")
                log_in_file("stream", json_value)
                value = json.loads(json_value)
                eventDocument(value)
            except:
                log("Exception: stream_loop") 
                log(traceback.format_exc())
        log("<stream_loop> Processed {} messages".format(len(get_response.data)))        
            
        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]

## -- eventDocument --------------------------------------------------------

def eventDocument(value):
    eventType = value["eventType"]
    # ex: /n/fr03kzmuvhtf/b/psql-public-bucket/o/country.pdf"
    # XXX resourcePath
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
        result = shared_oci.belgian(value)
    elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
        result = shared_oci.vision(value)
    elif resourceExtension in [".srt"]:
        log("IGNORE .srt")
        return
    elif resourceExtension in [".json"]:
        result = shared_oci.decodeJson(value)
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
        # This will create a SRT file in Object Storage that will create a second even with resourceExtension ".srt" 
        shared_oci.speech(value)
        return
    elif resourceExtension in [".tif",".pdf"]:
        # This will create a JSON file in Object Storage that will create a second even with resourceExtension "json" 
        shared_oci.documentUnderstanding(value)
        return
    elif resourceName.endswith("/"):
        # Ignore
        log("IGNORE /")
        return
    else:
        result = shared_oci.invokeTika(value)

    log_in_file("content", result["content"])
    if len(result["content"])==0:
       return 
    
    result["source_type"] = "OBJECT_STORAGE"

    # Summary 
    if len(result["content"])>250:
        result["summary"] = shared_oci.summarizeContent(value, result["content"])
    else:    
        result["summary"] = result["content"]
    
    # Delete Document in repository
    deleteDocument( result["path"] )

    # If no page, just add the content
    if result.get("pages") == None:
        result["pages"] = [ result["content"] ]

    shared_db.createDoc(result)        
                
## -- deleteDocument --------------------------------------------------------

def deleteDocument(path):
    log( "<deleteDocument>")
    shared_db.deleteDoc(path)
    log( "</deleteDocument>")

## -- main ------------------------------------------------------------------

ociMessageEndpoint = os.getenv('STREAM_MESSAGE_ENDPOINT')
ociStreamOcid = os.getenv('STREAM_OCID')

# stream_client = oci.streaming.StreamClient(config, service_endpoint=ociMessageEndpoint)
stream_client = oci.streaming.StreamClient(config = {}, service_endpoint=ociMessageEndpoint, signer=shared_oci.signer)

# A cursor can be created as part of a consumer group.
# Committed offsets are managed for the group, and partitions
# are dynamically balanced amongst consumers in the group.

while True:
    shared_db.initDbConn()
    group_cursor = stream_cursor(stream_client, ociStreamOcid, "app-group", "app-instance-1")
    stream_loop(stream_client, ociStreamOcid, group_cursor)
    shared_db.closeDbConn()
    time.sleep(30)
