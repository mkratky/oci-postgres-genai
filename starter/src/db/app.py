# Import
import oci
import time
import os
import json 
import time
import pathlib

from base64 import b64decode

# Constant
LOG_DIR = '/tmp/app_log'
UNIQUE_ID = "ID"

# Function
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
    with open(LOG_DIR+"/stream_"+UNIQUE_ID+".txt", "w") as text_file:
        text_file.write(value)

def simple_message_loop(client, stream_id, initial_cursor):
    cursor = initial_cursor
    while True:
        get_response = client.get_messages(stream_id, cursor, limit=10)
        # No messages to process. return.
        if not get_response.data:
            return

        # Process the messages
        print(" Read {} messages".format(len(get_response.data)))
        for message in get_response.data:
            if message.key is None:
                key = "Null"
            else:
                key = b64decode(message.key.encode()).decode()
            json_value = b64decode(message.value.encode()).decode(); 
            print("{}: {}".format(key,json_value))
            log_in_file("stream", json_value)
            value = json.loads(json_value)
            eventDocument(value)
            
        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]

def eventDocument(value):
    global UNIQUE_ID 
    UNIQUE_ID = time.strftime("%Y%m%d-%H%M%S-%f")

    eventType = value["eventType"]
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    # ex: /n/fr03kzmuvhtf/b/psql-public-bucket/o/country.pdf"
    # XXX OIC: resourcePath
    resourceId = value["data"]["resourceId"]
    print( eventType + " - " + resourceId ) 

    if eventType in ["com.oraclecloud.objectstorage.createobject", "com.oraclecloud.objectstorage.updateobject"]:
        insertDocument( value )
    elif eventType == "com.oraclecloud.objectstorage.deleteobject":
        deleteDocument( value )

def insertDocument(value):
    resourceName = value["data"]["resourceName"]
    lowerResourceName = resourceName.lower()
    resourceExtension = pathlib.Path(lowerResourceName)
    content = "-"
    if resourceName.startswith("belgian"):
      print ('BELGIAN TODO')
    elif resourceExtension in ["png", "jpg", "jpeg", "gif"]:
      print ('IMAGE TODO')
    elif resourceExtension in ["json"]:
      print ('JSON TODO')
    elif resourceExtension in ["mp3", "mp4", "avi", "wav", "m4a"]:
      print ('VOICE TODO')
    elif resourceExtension in ["tif"]:
      print ('DOCUNDERSTANDING TODO')
    elif resourceName.endswith("/"):
      print ('FOLDER TODO')
    else:
      invokeTika(value)
    var_content_1 = content
    log_in_file("content", content)

def invokeTika(value):
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["additionalDetails"]["resourceName"]
    
    invoke_client = functions.FunctionsInvokeClient(config = {}, service_endpoint=fnInvokeEndpoint)
    # {"bucketName": "xxx", "namespace": "xxx", "resourceName": "xxx"}
    req = '{"bucketName": "{bucketName}", "namespace": "{namespace}", "resourceName": "{resourceName}"}'.format(bucketName=bucketName, namespace=namespace, resourceName=resourceName)
    print( "Tika request: " + req)
    resp = invoke_client.invoke_function(fnOcid, invoke_function_body=req)
    print( "Tika response: " + resp.data.text)

def deleteDocument(value):
    print ('TODO')

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
group_cursor = get_cursor_by_group(stream_client, ociStreamOcid, "example-group", "example-instance-1")
simple_message_loop(stream_client, ociStreamOcid, group_cursor)
