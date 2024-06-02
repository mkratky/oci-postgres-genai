import oci
import os  

class OCICalls(object):
    def __init__(self):
        # generate signer
        self.generate_signer_from_instance_principals()
        # call apis
        self.get_namespace()


    def generate_signer_from_instance_principals(self):
        try:
            # get signer from instance principals token
            self.signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        except Exception:
            print("There was an error while trying to get the Signer")
            raise SystemExit
        # generate config info from signer
        self.config = {'region': self.signer.region, 'tenancy': self.signer.tenancy_id}


    def get_namespace(self):
        compartment_ocid = os.getenv('TF_VAR_compartment_ocid')
        object_storage_client = oci.object_storage.ObjectStorageClient(config = {}, signer=self.signer)
        namespace = object_storage_client.get_namespace(compartment_id=compartment_ocid).data
        print('Object storage namespace for compartment id {} is: {}'.format(compartment_ocid, namespace))
        print('\n=========================\n')


# Initiate process
OCICalls()

