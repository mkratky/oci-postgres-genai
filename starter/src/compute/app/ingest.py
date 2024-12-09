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
import document

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
    updateCount = 0
    cursor = initial_cursor
    while True:
        get_response = client.get_messages(stream_id, cursor, limit=10)
        # No messages to process. return.
        if not get_response.data:
            document.updateCount( updateCount )
            return

        # Process the messages
        log("<stream_loop> Read {} messages".format(len(get_response.data)))
        updateCount += len(get_response.data)
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
        document.insertDocument( value )
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        document.deleteDocument( value )

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
