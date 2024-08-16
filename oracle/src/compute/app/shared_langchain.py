# Import
import os
import shared_db
from shared_oci import log
from shared_oci import dictString
from shared_oci import dictInt

from langchain_core.documents import Document
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.embeddings import OCIGenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import DistanceStrategy
from typing import List, Tuple

# Globals
embeddings = OCIGenAIEmbeddings(
    model_id="cohere.embed-multilingual-v3.0",
    service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com",
    compartment_id=os.getenv("TF_VAR_compartment_ocid"),
    auth_type="INSTANCE_PRINCIPAL"
)

# -- insertDocsChunck -----------------------------------------------------------------

def insertDocsChunck(dbConn, result):  

    log("<langchain insertDocsChunck>")
    vectorstore = OracleVS( client=dbConn, table_name="docs_langchain", embedding_function=embeddings, distance_strategy=DistanceStrategy.DOT_PRODUCT )
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)      
    for pageNumber in result["pages"]:
        p = result["pages"][pageNumber]; 
        log(f"<langchain insertDocsChunck> Page {pageNumber}")
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
                    "page": pageNumber, 
                    "char_start": "0", 
                    "char_end": "0" 
                },
            )
        ]
        docs_chunck = text_splitter.split_documents(docs)
        print( docs_chunck )
        vectorstore.add_documents( docs_chunck )
    log("</langchain insertDocsChunck>")

# -- deleteDoc -----------------------------------------------------------------

def deleteDoc(dbConn, path):
    # XXXXX # There is no delete implemented in langchain pgvector..
    cur = dbConn.cursor()
    stmt = "delete FROM docs_langchain WHERE JSON_VALUE(metadata,'$.path')=:1"
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
    shared_db.initDbConn()
    vectorstore = OracleVS(
        embedding_function=embeddings,
        client=shared_db.dbConn,
        table_name="docs_langchain",
        distance_strategy=DistanceStrategy.DOT_PRODUCT,        
    )
    docs_with_score: List[Tuple[Document, float]] = vectorstore.similarity_search_with_score(question, k=10)
    shared_db.closeDbConn()

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

# select v.SQL_TEXT from v$sql v where lower(SQL_TEXT) like '%docs_langchain%'
# INSERT INTO docs_langchain (id, text, metadata, embedding) VALUES (:1, :2, :3, :4)
# SELECT id, text, metadata, vector_distance(embedding, :embedding,	DOT) as distance FROM docs_langchain ORDER BY distance FETCH APPROX FIRST 10 ROWS ONLY

