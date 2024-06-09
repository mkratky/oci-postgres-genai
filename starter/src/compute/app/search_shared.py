# Import
import oci
import os
import json 
import requests
import psycopg2

# Constant
LOG_DIR = '/tmp/app_log'
UNIQUE_ID = "ID"

# Connection
dbConn = None

## -- log ------------------------------------------------------------------

def log(s):
   print( s, flush=True)

## -- log_in_file --------------------------------------------------------

def log_in_file(prefix, value):
    global UNIQUE_ID
    # Create Log directory
    if os.path.isdir(LOG_DIR) == False:
        os.mkdir(LOG_DIR)     
    filename = LOG_DIR+"/"+prefix+"_"+UNIQUE_ID+".txt"
    with open(filename, "w") as text_file:
        text_file.write(value)
    log("log file: " +filename )  

## -- dictString ------------------------------------------------------------

def dictString(d,key):
   value = d.get(key)
   if value is None:
       return "-"
   else:
       return value  
   
## -- dictInt ------------------------------------------------------------

def dictInt(d,key):
   value = d.get(key)
   if value is None:
       return 0
   else:
       return int(value)     


## -- embedText ------------------------------------------------------

#XXXXX Ideally all vector should be created in one call
def embedText(c,signer):
    log( "<embedText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/embedText'
    body = {
        "inputs" : [ c ],
        "servingMode" : {
            "servingType" : "ON_DEMAND",
            "modelId" : "cohere.embed-english-light-v2.0"
        },
        "truncate" : "START",
        "compartmentId" : compartmentId
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("embedText_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    log( "</embedText>")
    return dictString(j,"embeddings")[0] 

## -- generateText ------------------------------------------------------

def generateText(prompt,signer):
    log( "<generateText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/generateText'
    body = {
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
            "servingType": "ON_DEMAND"
        },
        "inferenceRequest": {
            "prompt": prompt,
            "maxTokens": 600,
            "temperature": 0,
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "stopSequences": [],
            "runtimeType": "COHERE"
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("generateText_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["inferenceResponse"]["generatedTexts"][0]["text"]
    log( "</generateText>")
    return s


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
            dictString(result,"region"),
            dictString(result,"summary"),
            dictInt(result,"page")
        )
    ]
    try:
        cur.executemany(stmt, data)
        print(f"Successfully inserted {cur.rowcount} records.")
    except (Exception, psycopg2.Error) as error:
        print(f"Error inserting records: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()

# -- deleteDb -----------------------------------------------------------------

def deleteDb(path):  
    global dbConn
    cur = dbConn.cursor()
    stmt = "delete from oic where path=%s"
    try:
        cur.execute(stmt, (path,))
        print(f"<deleteDb> Successfully deleted")
    except (Exception, psycopg2.Error) as error:
        print(f"<deleteDb> Error deleting: {error}")
    finally:
        # Close the cursor and connection
        if cur:
            cur.close()


# -- queryDb ----------------------------------------------------------------------

def queryDb( type, question, embed ):
    query = "SELECT filename, path, content, content_type, region, page, summary FROM oic"
    if type=="search":
        # Text search example
        query += " WHERE content ILIKE '%{0}%'".format(question)
    elif type=="semantic":
        query += " ORDER BY cohere_embed <=> '{0}' LIMIT 10;".format(embed)
    elif type in ["hybrid","rag"] :
        query = """
        WITH text_search AS (
            SELECT id, ts_rank_cd(to_tsvector(content), plainto_tsquery('{0}')) AS text_rank
            FROM oic
            WHERE content @@ plainto_tsquery('{0}')
        ),
        vector_search AS (
            SELECT id, cohere_embed <=> '{1}' AS vector_distance
            FROM oic
        )
        SELECT o.filename, o.path, o.content, o.content_type, o.region, o.page, o.summary,
            (0.3 * ts.text_rank + 0.7 * (1 - vs.vector_distance)) AS hybrid_score
        FROM oic o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY hybrid_score DESC
        LIMIT 10;
        """.format(question,embed)
    else:
        log( "Not supported type " + type)
        return []
    result = [] 
    cursor = dbConn.cursor()
    cursor.execute(query)
    deptRows = cursor.fetchall()
    for row in deptRows:
        result.append( {"filename": row[0], "path": row[1], "content": row[2], "contentType": row[3], "region": row[4], "page": row[5], "summary": row[6]} )  
    for r in result:
        log("filename="+r["filename"])
        log("content: "+r["content"][:150])
    return result
