import oci  
import os  

from base64 import b64encode  
  
ociMessageEndpoint = os.getenv('STREAM_BOOSTRAPSERVER')
ociStreamOcid = os.getenv('STREAM_OCID')

def produce_messages(client, stream_id):
  # Build up a PutMessagesDetails and publish some messages to the stream
  message_list = []
  for i in range(100):
      key = "messageKey" + str(i)
      value = "messageValue " + str(i)
      encoded_key = b64encode(key.encode()).decode()
      encoded_value = b64encode(value.encode()).decode()
      message_list.append(oci.streaming.models.PutMessagesDetailsEntry(key=encoded_key, value=encoded_value))  
  
  print("Publishing {} messages to the stream {} ".format(len(message_list), stream_id))
  messages = oci.streaming.models.PutMessagesDetails(messages=message_list)
  put_message_result = client.put_messages(stream_id, messages)
  
  # The put_message_result can contain some useful metadata for handling failures
  for entry in put_message_result.data.entries:
      if entry.error:
          print("Error ({}) : {}".format(entry.error, entry.error_message))
      else:
          print("Published message to partition {} , offset {}".format(entry.partition, entry.offset))

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}
stream_client = oci.streaming.StreamClient(config = {}, service_endpoint=ociMessageEndpoint, signer=signer)

# Publish some messages to the stream
produce_messages(stream_client, ociStreamOcid)