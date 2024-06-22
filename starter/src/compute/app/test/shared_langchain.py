# See https://python.langchain.com/v0.2/docs/integrations/document_loaders/oracleai/
# Import
import os
import array
import oracledb
from shared_oci import log
from shared_oci import dictString
from shared_oci import dictInt

# Langchain
from langchain_community.document_loaders.oracleai import (
    OracleDocLoader,
    OracleTextSplitter,
)
from langchain_community.embeddings.oracleai import OracleEmbeddings
from langchain_community.utilities.oracleai import OracleSummary
from langchain_community.vectorstores import oraclevs
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

# Connection
dbConn = None

## -- initDbConn --------------------------------------------------------------

def initDbConn():
    global dbConn 
    # Thick driver...
    oracledb.init_oracle_client()
    dbConn = oracledb.connect( user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), dsn=os.getenv('DB_URL'))
    dbConn.autocommit = True

## -- closeDbConn --------------------------------------------------------------

def closeDbConn():
    global dbConn 
    dbConn.close()

# -- createDoc -----------------------------------------------------------------

def createDoc(result):  
    for p in result["pages"]:
        # Get Next Chunks
        chuncks = shared_oci.cutInChunks( p )
        for c in chuncks:
            result["cohereEmbed"] = shared_oci.embedText(c)
            insertDocChunck(result,c)

# -- insertDocChunck -----------------------------------------------------------------

def insertDocChunck(result,c):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO docs_chunck (
            application_name, author, translation, cohere_embed, content, content_type,
            creation_date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, summary, page
        )
        VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16, :17, :18)
    """
    data = [
        (dictString(result,"applicationName"), 
            dictString(result,"author"),
            dictString(result,"translation"),
            array.array("f", result["cohereEmbed"]),
            c,
            dictString(result,"contentType"),
            dictString(result,"creationDate"),
            dictString(result,"modified"),
            dictString(result,"other1"),
            dictString(result,"other2"),
            dictString(result,"other3"),
            dictString(result,"parsed_by"),
            dictString(result,"filename"),
            dictString(result,"path"),
            dictString(result,"publisher"),
            os.getenv("TF_VAR_region"),
            dictString(result,"summary"),
            dictInt(result,"page")
        )
    ]
    try:
        cur.executemany(stmt, data)
        print(f"Successfully inserted {cur.rowcount} records.")
    except (Exception) as error:
        print(f"Error inserting records: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- deleteDoc -----------------------------------------------------------------

def deleteDoc(path):  
    global dbConn
    cur = dbConn.cursor()
    stmt = "delete from docs_chunck where path=:1"
    log(f"<deleteDoc> path={path}")
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDoc> Successfully {cur.rowcount} deleted")
    except (Exception) as error:
        print(f"<deleteDoc> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- queryDb ----------------------------------------------------------------------

def queryDb( type, question, embed ):
    if type=="search":
        # Text search example
        query = """
        SELECT filename, path, TO_CHAR(SUBSTR(content,1,1000)) content_char, content_type, region, page, summary, score(99) FROM docs
        WHERE CONTAINS(content, {0}, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        """.format(question)
    elif type=="semantic":
        query = """
        SELECT filename, path, TO_CHAR(SUBSTR(content,1,1000)) content_char, content_type, region, page, summary, 1 score FROM docs
        ORDER BY cohere_embed <=> '{0}' FETCH FIRST 10 ROWS ONLY
        """.format(embed)
    elif type in ["hybrid","rag"]:
        query = """
        WITH text_search AS (
            SELECT id, score(99) as score FROM docs
            WHERE CONTAINS(content, {0}, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        ),
        vector_search AS (
            SELECT id, cohere_embed <=> '{1}' AS vector_distance
            FROM docs
        )
        SELECT o.filename, o.path, TO_CHAR(SUBSTR(content,1,1000)) content_char, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.score + 0.7 * (1 - vs.vector_distance)) AS score
        FROM docs o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY score DESC
        FETCH FIRST 10 ROWS ONLY;
        """.format(question,embed)
#        FULL OUTER JOIN text_search ts ON o.id = ts.id
#        FULL OUTER JOIN vector_search vs ON o.id = vs.id

    else:
        log( "Not supported type " + type)
        return []
    result = [] 
    cursor = dbConn.cursor()
    cursor.execute(query)
    deptRows = cursor.fetchall()
    for row in deptRows:
        result.append( {"filename": row[0], "path": row[1], "content": row[2], "contentType": row[3], "region": row[4], "page": row[5], "summary": row[6], "score": row[7]} )  
    for r in result:
        log("filename="+r["filename"])
        log("content: "+r["content"][:150])
    return result



# ----

def insertData():
    """
    In this sample example, we will use 'database' provider for both summary and embeddings.
    So, we don't need to do the followings:
        - set proxy for 3rd party providers
        - create credential for 3rd party providers

    If you choose to use 3rd party provider, 
    please follow the necessary steps for proxy and credential.
    """

    # oracle connection
    # please update with your username, password, hostname, and service_name
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    dsn = os.getenv('DB_URL')

    try:
        conn = oracledb.connect(user=username, password=password, dsn=dsn)
        print("Connection successful!")
    except Exception as e:
        print("Connection failed!")
        sys.exit(1)


    # load onnx model
    # please update with your related information
    onnx_dir = "DEMO_PY_DIR"
    onnx_file = "tinybert.onnx"
    model_name = "demo_model"
    try:
        OracleEmbeddings.load_onnx_model(conn, onnx_dir, onnx_file, model_name)
        print("ONNX model loaded.")
    except Exception as e:
        print("ONNX model loading failed!")
        sys.exit(1)

    # params
    # please update necessary fields with related information
    loader_params = {
        "owner": username,
        "tablename": "demo_tab",
        "colname": "data",
    }
    summary_params = {
        "provider": "database",
        "glevel": "S",
        "numParagraphs": 1,
        "language": "english",
    }
    splitter_params = {"normalize": "all"}
    embedder_params = {"provider": "database", "model": "demo_model"}

    # instantiate loader, summary, splitter, and embedder
    loader = OracleDocLoader(conn=conn, params=loader_params)
    summary = OracleSummary(conn=conn, params=summary_params)
    splitter = OracleTextSplitter(conn=conn, params=splitter_params)
    embedder = OracleEmbeddings(conn=conn, params=embedder_params)

    # process the documents
    chunks_with_mdata = []
    for id, doc in enumerate(docs, start=1):
        summ = summary.get_summary(doc.page_content)
        chunks = splitter.split_text(doc.page_content)
        for ic, chunk in enumerate(chunks, start=1):
            chunk_metadata = doc.metadata.copy()
            chunk_metadata["id"] = chunk_metadata["_oid"] + "$" + str(id) + "$" + str(ic)
            chunk_metadata["document_id"] = str(id)
            chunk_metadata["document_summary"] = str(summ[0])
            chunks_with_mdata.append(
                Document(page_content=str(chunk), metadata=chunk_metadata)
            )

    """ verify """
    print(f"Number of total chunks with metadata: {len(chunks_with_mdata)}")

    # create Oracle AI Vector Store
    vectorstore = OracleVS.from_documents(
        chunks_with_mdata,
        embedder,
        client=conn,
        table_name="oravs",
        distance_strategy=DistanceStrategy.DOT_PRODUCT,
    )

    """ verify """
    print(f"Vector Store Table: {vectorstore.table_name}")   

    oraclevs.create_index(
        conn, vectorstore, params={"idx_name": "hnsw_oravs", "idx_type": "HNSW"}
    )
    print("Index created.")     


    query = "What is Oracle AI Vector Store?"
    filter = {"document_id": ["1"]}

    # Similarity search without a filter
    print(vectorstore.similarity_search(query, 1))

    # Similarity search with a filter
    print(vectorstore.similarity_search(query, 1, filter=filter))

    # Similarity search with relevance score
    print(vectorstore.similarity_search_with_score(query, 1))

    # Similarity search with relevance score with filter
    print(vectorstore.similarity_search_with_score(query, 1, filter=filter))

    # Max marginal relevance search
    print(vectorstore.max_marginal_relevance_search(query, 1, fetch_k=20, lambda_mult=0.5))

    # Max marginal relevance search with filter
    print(
        vectorstore.max_marginal_relevance_search(
            query, 1, fetch_k=20, lambda_mult=0.5, filter=filter
        )
    )


insertData()
loadLocalFiles()
