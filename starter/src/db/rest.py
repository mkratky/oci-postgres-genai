import os
import traceback
from flask import Flask
from flask import jsonify
from flask_cors import CORS
import psycopg2
import search_shared

app = Flask(__name__)
CORS(app)

@app.route('/query')
def query():
    a = []
    type = request.args.get('type')
    question = request.args.get('question')
    search_shared.log( "----------------------------------------")
    search_shared.log( "type: " + type)
    search_shared.log( "question: " + question)
    try:
        search_shared.initDbConn()
        embed = search_shared.embedText(question,signer)
        a = search_shared.queryDb( type, question, embed) 
        if type=="rag":
            # XX TODO
            search_shared.genai( question, a )    
    finally:
        search_shared.closeDbConn()

    response = jsonify(a)
    response.status_code = 200
    return response   

@app.route('/info')
def info():
        return "Python - Flask - PSQL"          

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

