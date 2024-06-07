# Import
import oci
import sys
import search_shared

## -- main ------------------------------------------------------------------

# Instance Principal
global signer
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

print(sys.argv)
if len(sys.argv)<2:
    search_shared.log( "Usage: search_query.py <type=text/vector/hybrid/rag> question")
    exit(1)
type=sys.argv[1];
question=sys.argv[2];
search_shared.log( "type: " + type)
search_shared.log( "question: " + question)
embed = search_shared.embedText(question,signer)

search_shared.initDbConn()
result = search_shared.queryDb( type, question, embed) 
search_shared.closeDbConn()

if type=="rag":
    # XX TODO
    search_shared.genai( question, result )

