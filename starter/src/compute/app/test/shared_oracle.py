# Import
import os
import array
import oracledb
from shared_oci import log
from shared_oci import dictString
from shared_oci import dictInt

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

# -- insertDoc -----------------------------------------------------------------

def insertDoc(result,c):  
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
        SELECT filename, path, TO_CHAR(SUBSTR(content,1,1000)) content_char, content_type, region, page, summary, score(99) FROM docs_chunck
        WHERE CONTAINS(content, {0}, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        """.format(question)
    elif type=="semantic":
        query = """
        SELECT filename, path, TO_CHAR(SUBSTR(content,1,1000)) content_char, content_type, region, page, summary, 1 score FROM docs_chunck
        ORDER BY cohere_embed <=> '{0}' FETCH FIRST 10 ROWS ONLY
        """.format(embed)
    elif type in ["hybrid","rag"]:
        query = """
        WITH text_search AS (
            SELECT id, score(99) as score FROM docs_chunck
            WHERE CONTAINS(content, {0}, 99)>0 order by score(99) DESC FETCH FIRST 10 ROWS ONLY
        ),
        vector_search AS (
            SELECT id, cohere_embed <=> '{1}' AS vector_distance
            FROM docs_chunck
        )
        SELECT o.filename, o.path, TO_CHAR(SUBSTR(content,1,1000)) content_char, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.score + 0.7 * (1 - vs.vector_distance)) AS score
        FROM docs_chunck o
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



