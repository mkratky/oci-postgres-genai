import os
import traceback
from flask import Flask
from flask import jsonify
from flask_cors import CORS
import psycopg2

app = Flask(__name__)
CORS(app)

@app.route('/dept')
def dept():
    a = []
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_URL'),
            database="postgres",
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            sslmode='require' )
        print("Successfully connected to database", flush=True)
        cursor = conn.cursor()
        cursor.execute("SELECT deptno, dname, loc FROM dept")
        deptRows = cursor.fetchall()
        for row in deptRows:
            a.append( {"deptno": row[0], "dname": row[1], "loc": row[2]} )        
    except Exception as e:
        print(traceback.format_exc(), flush=True)
        print(e, flush=True)
    finally:
        cursor.close() 
        conn.close() 
    response = jsonify(a)
    response.status_code = 200
    return response   

@app.route('/info')
def info():
        return "Python - Flask - PSQL"          

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

