from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS
import shared_oci
from shared_oci import log
import shared_db
import oci

app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['GET','POST'])
def query():
    a = []
    if request.method=='POST':
        type = request.json.get('type')
        question = request.json.get('question')
    else:
        type = request.args.get('type')
        question = request.args.get('question')
    log( "----------------------------------------")
    log( "type: " + str(type))
    log( "question: " + str(question))
    try:
        shared_db.initDbConn()
        embed = shared_oci.embedText(question)
        a = shared_db.queryDb( type, question, embed) 
    finally:
        shared_db.closeDbConn()

    response = jsonify(a)
    response.status_code = 200
    return response   

@app.route('/generate', methods=['GET','POST'])
def generate():
    if request.method=='POST':
        prompt = request.json.get('prompt')
    else:
        prompt = request.args.get('prompt')
    result = shared_oci.generateText( prompt )  
    log("Result="+str(result))  
    return str(result)   

@app.route('/chat', methods=['GET','POST'])
def chat():
    if request.method=='POST':
        prompt = request.json.get('messages')
    else:
        prompt = request.args.get('messages')
    result = shared_oci.llama_chat( messages )  
    log("Result="+str(result))  
    return str(result)  

@app.route('/info')
def info():
        return "Python - Flask - PSQL"          


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

