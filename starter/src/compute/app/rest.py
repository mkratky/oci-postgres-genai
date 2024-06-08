from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS
import search_shared
import oci

app = Flask(__name__)
CORS(app)

# OCI
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

@app.route('/query')
def query():
    global signer
    a = []
    type = request.args.get('type')
    question = request.args.get('question')
    search_shared.log( "----------------------------------------")
    search_shared.log( "type: " + str(type))
    search_shared.log( "question: " + str(question))
    try:
        search_shared.initDbConn()
        embed = search_shared.embedText(question, signer)
        a = search_shared.queryDb( type, question, embed) 
    finally:
        search_shared.closeDbConn()

    response = jsonify(a)
    response.status_code = 200
    return response   

@app.route('/generateText')
def generateText():
    global signer
    prompt = request.args.get('prompt')
    result = search_shared.generateText( prompt, signer )    
    response = jsonify(a)
    response.status_code = 200
    return response   

@app.route('/info')
def info():
        return "Python - Flask - PSQL"          



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

