# Import
import oci
import os
import json 
import time
import pathlib
import requests
import pprint
import psycopg2

from psycopg2.extras import execute_values
from datetime import datetime
from base64 import b64decode

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

## -- dictValue ------------------------------------------------------------

def dictValue(d,key):
   value = d.get(key)
   if value is None:
       return "-"
   else:
       return value  


## -- embedText ------------------------------------------------------

#XXXXX Ideally all vector should be created in one call
def embedText(c):
    log( "<embedText>")
    global signer
    compartmentId = os.getEnv("TF_VAR_compartment_ocid")
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
    return dictValue(j,"embeddings")[0] 

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

def insertDb(result):  
    global dbConn
    cur = dbConn.cursor()
    stmt = """
        INSERT INTO oic (
            application_name, author, translation, cohere_embed, content, content_type,
            creation_date, date, modified, other1, other2, other3, parsed_by,
            filename, path, publisher, region, context
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    data = [
        (dictValue(result,"applicationName"), 
            dictValue(result,"author"),
            dictValue(result,"translation"),
            dictValue(result,"cohereEmbed"),
            dictValue(result,"content"),
            dictValue(result,"contentType"),
            dictValue(result,"creationDate"),
            dictValue(result,"date"),
            dictValue(result,"modified"),
            dictValue(result,"other1"),
            dictValue(result,"other2"),
            dictValue(result,"other3"),
            dictValue(result,"parsed_by"),
            dictValue(result,"filename"),
            dictValue(result,"path"),
            dictValue(result,"publisher"),
            dictValue(result,"region"),
            dictValue(result,"context")
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
    query = "SELECT path, content, content_type FROM oic"
    if type=="text":
        # Text search example
        query += " WHERE content ILIKE '%"+question+"%'"
    elif type=="vector":
        query += " ORDER BY cohere_embed <=> '"+embed+"'+ LIMIT 10;"
    elif type=="hybrid":
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
        SELECT o.id, o.content, 
            (0.3 * ts.text_rank + 0.7 * (1 - vs.vector_distance)) AS hybrid_score
        FROM oic o
        JOIN text_search ts ON o.id = ts.id
        JOIN vector_search vs ON o.id = vs.id
        ORDER BY hybrid_score DESC
        LIMIT 10;
        """.format(question,embed)
    else:
        log( "Not supported type " + type)
    result = [] 
    cursor = dbConn.cursor()
    cursor.execute(query)
    deptRows = cursor.fetchall()
    for row in deptRows:
        result.append( {"path": row[0], "content": row[1], "contentType": row[2]} )  
    log( result )

