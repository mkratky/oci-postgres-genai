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

# -- insertDb -----------------------------------------------------------------

def insertDb(result,c):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO oic (
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

# -- deleteDb -----------------------------------------------------------------

def deleteDb(path):  
    global dbConn
    cur = dbConn.cursor()
    stmt = "delete from oic where path=:1"
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDb> Successfully deleted")
    except (Exception) as error:
        print(f"<deleteDb> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()


# -- queryDb ----------------------------------------------------------------------

def queryDb( type, question, embed ):
    result = [] 
    cursor = dbConn.cursor()
    query = "SELECT filename, path, content, content_type, region, page, summary FROM oic"
    if type=="search":
        # Text search example
        query += " WHERE content ILIKE '%{0}%'".format(question)
        cursor.execute(query)
    elif type=="semantic":
        query += " ORDER BY VECTOR_DISTANCE( cohere_embed, :1, EUCLIDEAN ) FETCH EXACT FIRST 10 ROWS ONLY;"
        cursor.execute(query, embed)
    elif type in ["hybrid","rag"] :
        query = """
        WITH text_search AS (
            SELECT id, SCORE(10) text_rank FROM oic WHERE CONTAINS (content, 'about :2', 10)
           ),
        vector_search AS (
            SELECT id, VECTOR_DISTANCE( cohere_embed, :2, EUCLIDEAN ) AS vector_distance
            FROM oic
        )
        SELECT o.filename, o.path, o.content, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.text_rank + 0.7 * (1 - vs.vector_distance)) AS hybrid_score
        FROM oic o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY hybrid_score DESC
        FETCH EXACT FIRST 10 ROWS ONLY;
        """
        cursor.execute(query, question, embed)
    else:
        log( "Not supported type " + type)
        return []
    deptRows = cursor.fetchall()
    for row in deptRows:
        result.append( {"filename": row[0], "path": row[1], "content": row[2], "contentType": row[3], "region": row[4], "page": row[5], "summary": row[6]} )  
    for r in result:
        log("filename="+r["filename"])
        log("content: "+r["content"][:150])
    return result


