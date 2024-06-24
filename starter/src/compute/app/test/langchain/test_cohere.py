from langchain_community.llms import OCIGenAI
import oci
import os

# use default authN method API-key
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner() #preferred way but policies needs to be in place to enable instance principal or resource principal https://docs.oracle.com/en-us/iaas/data-flow/using/resource-principal-policies.htm
compartmentId = os.getenv("TF_VAR_compartment_ocid")

llm = OCIGenAI(
    model_id="cohere.command",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=compartmentId,
    auth_type="INSTANCE_PRINCIPAL",
)

response = llm.invoke("Tell me one fact about earth", temperature=0.7)
print(response)