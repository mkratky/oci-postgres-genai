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
    search_shared.log( "type: " + type)
    search_shared.log( "question: " + question)
    try:
        if type=='generate':
            prompt = "You are a program answering with a simple clear response of one sentence. Question: " + question
            search_shared.genai( prompt, signer )  
        else:
            search_shared.initDbConn()
            embed = search_shared.embedText(question, signer)
            a = search_shared.queryDb( type, question, embed) 
            if type=="rag":
                prompt = """You are a person answering questions in a predefined json format based on 3 rules. The question is: "${$page.variables.searchText}". 
                    To respond to the question, follow the 3 following rules:
                    1. Answer the question only based on the json documents below
                    2. If the answer is not found in the content of the documents below, say "I do not find the answer in the documents." 
                    3. The answer has the following json format: { "found": "Boolean response found in document", "document": "Document where the response is found", "response": "response of the question"}

                    JSON document
                    ["""
                bFirst = True
                for doc in a:
                    if bFirst:
                        bFirst = False
                    else:
                        prompt += ","
                    prompt += """{ "Document": "{0}",
                        "Context": "",
                        "Sentence": "{1}" }`;
                                }
                                prompt += ']'
                """.format(a["filename"], a["content"])
                search_shared.log("prompt: " + prompt )
                search_shared.genai( prompt, a )    
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

