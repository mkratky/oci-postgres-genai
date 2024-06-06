# Import
import oci
import os
import shared

## -- main ------------------------------------------------------------------

# Instance Principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

print(sys.argv)
type=sys.argv[0];
question=sys.argv[1];
log( "type:" + type)
log( "question:" + question)
embed = shared.embedText(c)

shared.initDbConn()
result = shared.queryDb( type, question, embed) 
shared.closeDbConn()

if type=="rag":
    shared.genai( question, result )

