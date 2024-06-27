# Import
import os
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
compartmentId = os.getenv("TF_VAR_compartment_ocid")

embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=compartmentId,
    auth_type="INSTANCE_PRINCIPAL"
)

# -- insertDocsChunck -----------------------------------------------------------------

def insertDocsChunck(result):  
    return
    log("<langchain insertDocsChunck>")
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
    log("</langchain insertDocsChunck>")

# -- deleteDoc -----------------------------------------------------------------

def deleteDoc(dbConn, path):
    return

    # XXXXX # There is no delete implemented in langchain pgvector..
    cur = dbConn.cursor()
    stmt = "delete FROM langchain_pg_embedding WHERE cmetadata->>'path'=%s"
    log(f"<langchain deleteDoc> path={path}")
    try:
        cur.execute(stmt, (path,))
        print(f"<langchain deleteDoc> Successfully {cur.rowcount} deleted")
    except (Exception) as error:
        print(f"<langchain deleteDoc> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()    
    # delete FROM langchain_pg_embedding WHERE cmetadata->>'path'='/n/fr03kzmuvhtf/b/psql-public-bucket/o/disco.pdf';

# -- queryDb ----------------------------------------------------------------------

def queryDb( question ):
    docs_with_score: List[Tuple[Document, float]] = vectorstore.similarity_search_with_score(question, k=10)

    result = [] 
    for doc, score in docs_with_score:
        result.append( 
            {
                "filename": doc.metadata['filename'], 
                "path": doc.metadata['path'], 
                "content": doc.page_content, 
                "contentType": doc.metadata['content_type'], 
                "region": doc.metadata['region'], 
                "page": doc.metadata['page'], 
                "summary": doc.metadata['summary'], 
                "score": score 
            }) 
    return result

