from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import OCIGenAI
from langchain_core.prompts import PromptTemplate
import oci
import os

# use default authN method API-key
oci_signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner() #preferred way but policies needs to be in place to enable instance principal or resource principal https://docs.oracle.com/en-us/iaas/data-flow/using/resource-principal-policies.htm
compartmentId = os.getenv("TF_VAR_compartment_ocid")

embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=compartmentId,
    auth_type="INSTANCE_PRINCIPAL"
)

vectorstore = FAISS.from_texts(
    [
        "Larry Ellison co-founded Oracle Corporation in 1977 with Bob Miner and Ed Oates.",
        "Oracle Corporation is an American multinational computer technology company headquartered in Austin, Texas, United States.",
    ],
    embedding=embeddings,
)

retriever = vectorstore.as_retriever()
template = """Answer the question based only on the following context:
{context}
 
Question: {question}
"""
prompt = PromptTemplate.from_template(template)

llm = OCIGenAI(
    model_id="cohere.command",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=compartmentId,
    auth_type="INSTANCE_PRINCIPAL",
)

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

print(chain.invoke("when was oracle founded?"))
print(chain.invoke("where is oracle headquartered?"))
