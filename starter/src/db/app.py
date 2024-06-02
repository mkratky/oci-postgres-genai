import oci
import time

from base64 import b64decode

ociMessageEndpoint = os.getenv('STREAM_BOOSTRAPSERVER')
ociStreamOcid = os.getenv('STREAM_OCID')

def generate_signer_from_instance_principals(self):
    try:
        # get signer from instance principals token
        self.signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    except Exception:
        print("There was an error while trying to get the Signer")
        raise SystemExit   
    # generate config info from signer
    self.config = {'region': self.signer.region, 'tenancy': self.signer.tenancy_id}


def get_cursor_by_group(sc, sid, group_name, instance_name):
    print(" Creating a cursor for group {}, instance {}".format(group_name, instance_name))
    cursor_details = oci.streaming.models.CreateGroupCursorDetails(group_name=group_name, instance_name=instance_name,
                                                                   type=oci.streaming.models.
                                                                   CreateGroupCursorDetails.TYPE_TRIM_HORIZON,
                                                                   commit_on_get=True)
    response = sc.create_group_cursor(sid, cursor_details)
    return response.data.value

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
            print("{}: {}".format(key,
                                  b64decode(message.value.encode()).decode()))

        # get_messages is a throttled method; clients should retrieve sufficiently large message
        # batches, as to avoid too many http requests.
        time.sleep(1)
        # use the next-cursor for iteration
        cursor = get_response.headers["opc-next-cursor"]

generate_signer_from_instance_principals()
config = oci.config.from_file(ociConfigFilePath, ociProfileName)
stream_client = oci.streaming.StreamClient(config, service_endpoint=ociMessageEndpoint)

# A cursor can be created as part of a consumer group.
# Committed offsets are managed for the group, and partitions
# are dynamically balanced amongst consumers in the group.
group_cursor = get_cursor_by_group(stream_client, ociStreamOcid, "example-group", "example-instance-1")
simple_message_loop(stream_client, ociStreamOcid, group_cursor)
