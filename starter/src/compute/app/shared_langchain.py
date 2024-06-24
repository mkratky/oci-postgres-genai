# Import
import os
import shared_oci 
from shared_oci import log
from shared_oci import dictString
from shared_oci import dictInt

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from typing import List, Tuple

# Globals
connection = "postgresql+psycopg://"+os.getenv('DB_USER')+":"+os.getenv('DB_PASSWORD')+"@"+os.getenv('DB_URL')+":5432/postgres"  # Uses psycopg3!
print( connection )
compartmentId = os.getenv("TF_VAR_compartment_ocid")

embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=compartmentId,
    auth_type="INSTANCE_PRINCIPAL"
)

vectorstore = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)

# -- insertDocsChunck -----------------------------------------------------------------

def insertDocsChunck(result):  
    docs = [
        Document(
            page_content=dictString(result,"content"),
            metadata=
            {
                "doc_id": dictInt(result,"docId"), 
                "translation": dictString(result,"translation"), 
                "content_type": dictString(result,"contentType"),
                "filename": dictString(result,"filename"), 
                "path": dictString(result,"path"), 
                "region": os.getenv("TF_VAR_region"), 
                "summary": dictString(result,"summary"), 
                "page": dictInt(result,"page"), 
                "char_start": "0", 
                "char_end": "0" 
            },
        )
    ]
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs_chunck = text_splitter.split_documents(docs)
    db = PGVector.from_documents(
        embedding=embeddings,
        documents=docs_chunck,
        collection_name="docs",
        connection=connection
    )

# -- deleteDoc -----------------------------------------------------------------

def deleteDoc(path):  
    docs = vectorstore.similarity_search("", filter={{"path": path}} )    
    print("count before", vectorstore._collection.count())
    for doc, score in docs:
        vectorstore._collection.delete(doc.id)
    print("count after", vectorstore._collection.count())

# -- queryDb ----------------------------------------------------------------------

def queryDb( question ):
    docs_with_score: List[Tuple[Document, float]] = db.similarity_search_with_score(question, k=10)

    result = [] 
    for doc, score in docs_with_score:
        result.append( 
            {
                "filename": doc.metadata['filename'], 
                "path": doc.metadata['path'], 
                "content": doc.page_content, 
                "contentType": doc.metadata['contentType'], 
                "region": doc.metadata['region'], 
                "page": doc.metadata['page'], 
                "summary": doc.metadata['summary'], 
                "score": score 
            }) 

