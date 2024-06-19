# Import
import os
import psycopg2
from shared_oci import log
from shared_oci import dictString
from shared_oci import dictInt

# Connection
dbConn = None

## -- initDbConn --------------------------------------------------------------

def initDbConn():
    global dbConn 
    dbConn = psycopg2.connect(dbname="postgres", user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_URL'))
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
            creation_date, date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, summary, page
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    data = [
        (dictString(result,"applicationName"), 
            dictString(result,"author"),
            dictString(result,"translation"),
            dictString(result,"cohereEmbed"),
            c,
            dictString(result,"contentType"),
            dictString(result,"creationDate"),
            dictString(result,"date"),
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
        log(f"Successfully inserted {cur.rowcount} records.")
    except (Exception, psycopg2.Error) as error:
        log(f"Error inserting records: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- deleteDb -----------------------------------------------------------------

def deleteDb(path):  
    global dbConn
    cur = dbConn.cursor()
    stmt = "delete from oic where path=%s"
    log(f"<deleteDb> path={path}")
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDb> Successfully {cur.rowcount} deleted")
    except (Exception, psycopg2.Error) as error:
        print(f"<deleteDb> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()


# -- queryDb ----------------------------------------------------------------------

def queryDb( type, question, embed ):
    if type=="search":
        # Text search example
        query = """
        SELECT filename, path, content, content_type, region, page, summary, ts_rank_cd(to_tsvector(content), plainto_tsquery('{0}')) score FROM oic
        WHERE to_tsvector(content) @@ plainto_tsquery('{0}') order by score DESC LIMIT 10
        """.format(question)
    elif type=="semantic":
        query = """
        SELECT filename, path, content, content_type, region, page, summary, 1 score FROM oic
        ORDER BY cohere_embed <=> '{0}' LIMIT 10
        """.format(embed)
    elif type in ["hybrid","rag"]:
        query = """
        WITH text_search AS (
            SELECT id, ts_rank_cd(to_tsvector(content), plainto_tsquery('{0}')) AS text_rank
            FROM oic
            WHERE to_tsvector(content) @@ plainto_tsquery('{0}')
        ),
        vector_search AS (
            SELECT id, cohere_embed <=> '{1}' AS vector_distance
            FROM oic
        )
        SELECT o.filename, o.path, o.content, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.text_rank + 0.7 * (1 - vs.vector_distance)) AS score
        FROM oic o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY score DESC
        LIMIT 10;
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


