# Import
import os
import json 
import requests
import oci

# Constant
LOG_DIR = '/tmp/app_log'
UNIQUE_ID = "ID"

# Signer
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

# Create Log directory
if os.path.isdir(LOG_DIR) == False:
    os.mkdir(LOG_DIR) 

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
def embedText(c):
    global signer
    log( "<embedText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/embedText'
    body = {
        "inputs" : [ c ],
        "servingMode" : {
            "servingType" : "ON_DEMAND",
            "modelId" : "cohere.embed-multilingual-v3.0"
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

def generateText(prompt):
    global signer
    log( "<generateText>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/generateText'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-16k",
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

## -- llama ------------------------------------------------------

def llama_chat(messages):
    """
            Messages format:
            "messages": [
            {
                "role": "USER",
                "content": [
                    {
                        "type": "TEXT",
                        "text": "write a python code that counts from 1 to 20"
                    }
                ]
            },
            {
                "role": "ASSISTANT",
                "content": [
                    {
                        "type": "TEXT",
                        "text": "Here is a simple Python code that counts from 1 to 20:\n```\nfor i in range(1, 21):\n    print(i)\n```\nExplanation:\n\n* `range(1, 21)` generates a sequence of numbers from 1 to 20 (inclusive).\n* The `for` loop iterates over this sequence, assigning each number to the variable `i`.\n* The `print(i)` statement prints the current value of `i` to the console.\n\nWhen you run this code, you should see the numbers 1 to 20 printed to the console, one per line.\n\nAlternatively, you can use a `while` loop to achieve the same result:\n```\ni = 1\nwhile i <= 20:\n    print(i)\n    i += 1\n```\nBut the `for` loop is generally more concise and Pythonic!"
                    }
                ]
            }            
    """
    global signer
    log( "<llama_chat>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-16k",
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "meta.llama-3-70b-instruct",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "maxTokens": 600,
            "temperature": 0,
            "preambleOverride": "",
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "chatHistory": [],
            "messages": messages,
            "apiFormat": "GENERIC"
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("llama_chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]["text"]
    if s.startswith('```json'):
        start_index = s.find("{") 
        end_index = s.rfind("}")+1
        s = s[start_index:end_index]
    log( "</llama_chat>")
    return s

## -- chat ------------------------------------------------------

def cohere_chat(prompt):
    global signer
    log( "<chat>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-16k",
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "cohere.command-r-16k",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "maxTokens": 600,
            "temperature": 0,
            "preambleOverride": "",
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
            "chatHistory": [],
            "message": prompt,
            "apiFormat": "COHERE"
        }
    }
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]["text"]
    if s.startswith('```json'):
        start_index = s.find("{") 
        end_index = s.rfind("}")+1
        s = s[start_index:end_index]
    log( "</chat>")
    return s

## -- invokeTika ------------------------------------------------------------------

def invokeTika(value):
    global signer
    log( "<invokeTika>")
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    invoke_client = oci.functions.FunctionsInvokeClient(config = {}, service_endpoint=fnInvokeEndpoint, signer=signer)
    # {"bucketName": "xxx", "namespace": "xxx", "resourceName": "xxx"}
    req = '{"bucketName": "' + bucketName + '", "namespace": "' + namespace + '", "resourceName": "' + resourceName + '"}'
    log( "Tika request: " + req)
    resp = invoke_client.invoke_function(fnOcid, invoke_function_body=req)
    log_in_file("tika_resp", resp.data.text) 
    j = json.loads(resp.data.text)
    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "applicationName": "Tika Parser",
        "modified": UNIQUE_ID,
        "contentType": dictString(j,"Content-Type"),
        "parsedBy": dictString(j,"X-Parsed-By"),
        "creationDate": UNIQUE_ID,
        "author": dictString(j,"Author"),
        "publisher": dictString(j,"publisher"),
        "content": j["content"],
        "path": resourceId
    }
    log( "</invokeTika>")
    return result

## -- summarizeContent ------------------------------------------------------

def summarizeContent(value,content):
    log( "<summarizeContent>")
    global signer
    compartmentId = value["data"]["compartmentId"]
    endpoint = 'https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/summarizeText'
    # Avoid Limit of 4096 Tokens
    if len(content) > 12000:
        log( "Truncating to 12000 characters")
        content = content[:12000]

    body = {
        "input" : content,
        "servingMode" : {
            "modelId" : "cohere.command",
            "servingType" : "ON_DEMAND"
        },
        "temperature" : 1,
        "length" : "AUTO",
        "extractiveness" : "AUTO",
        "format" : "AUTO",
        "additionalCommand" : "",
        "compartmentId" : compartmentId
    }
    try: 
        resp = requests.post(endpoint, json=body, auth=signer)
        resp.raise_for_status()
        log(resp)   
        log_in_file("summarizeContent_resp",str(resp.content)) 
        j = json.loads(resp.content)   
        log( "</summarizeContent>")
        return dictString(j,"summary") 
    except requests.exceptions.HTTPError as err:
        log("Exception: summarizeContent") 
        log(err.response.status_code)
        log(err.response.text)
        return "-"
    
## -- vision --------------------------------------------------------------

def vision(value):
    log( "<vision>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log_in_file("vision_resp", str(resp.data)) 

    concat_imageText = ""
    for l in resp.data.image_text.lines:
      concat_imageText += l.text + " "
    log("concat_imageText: " + concat_imageText )

    concat_labels = ""
    for l in resp.data.labels:
      concat_labels += l.name + " "
    log("concat_labels: " +concat_labels )

    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "Image",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": concat_imageText + " " + concat_labels,
        "path": resourceId,
        "other1": concat_labels
    }
    log( "</vision>")
    return result    

## -- belgian --------------------------------------------------------------

def belgian(value):
    log( "<belgian>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]
    resourceId = value["data"]["resourceId"]

    vision_client = oci.ai_vision.AIServiceVisionClient(config = {}, signer=signer)
    job = {
        "compartmentId": compartmentId,
        "image": {
            "source": "OBJECT_STORAGE",
            "bucketName": bucketName,
            "namespaceName": namespace,
            "objectName": resourceName
        },
        "features": [
            {
                    "featureType": "IMAGE_CLASSIFICATION",
                    "maxResults": 5
            },
            {
                    "featureType": "TEXT_DETECTION"
            }
        ]
    }
    resp = vision_client.analyze_image(job)
    log(resp.data)
    # log(json.dumps(resp,sort_keys=True, indent=4))

    name = resp.data.image_text.lines[8]
    id = resp.data.image_text.lines[19]
    birthdate = resp.data.image_text.lines[22]

    result = {
        "filename": resourceName,
        "date": UNIQUE_ID,
        "modified": UNIQUE_ID,
        "contentType": "Belgian ID",
        "parsedBy": "OCI Vision",
        "creationDate": UNIQUE_ID,
        "content": "Belgian identity card. Name="+name,
        "path": resourceId,
        "other1": id,
        "other2": birthdate,
    }
    log( "</belgian>")
    return result  

## -- speech --------------------------------------------------------------

def speech(value):
    log( "<speech>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]

    speech_client = oci.ai_speech.AIServiceSpeechClient(config = {}, signer=signer)
    job = {
        "normalization": {
                "isPunctuationEnabled": True
        },
        "compartmentId": compartmentId,
        "displayName": UNIQUE_ID,
        "modelDetails": {
                "domain": "GENERIC",
                "languageCode": "en-US"
        },
        "inputLocation": {
                "locationType": "OBJECT_LIST_INLINE_INPUT_LOCATION",
                "objectLocations": [
                    {
                            "namespaceName": namespace,
                            "bucketName": bucketName,
                            "objectNames": [
                                resourceName
                            ]
                    }
                ]
        },
        "outputLocation": {
                "namespaceName": namespace,
                "bucketName": bucketName,
                "prefix": "speech"
        },
        "additionalTranscriptionFormats": [
                "SRT"
        ]
    }
    resp = speech_client.create_transcription_job(job)
    log_in_file("speech_resp",str(resp.data))
    log( "</speech>")

## -- documentUnderstanding -------------------------------------------------

def documentUnderstanding(value):
    log( "<documentUnderstanding>")
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    compartmentId = value["data"]["compartmentId"]

    document_understanding_client = oci.ai_document.AIServiceDocumentClient(config = {}, signer=signer)
    job = {
        "processorConfig": {
            "language": "ENG",
            "processorType": "GENERAL",
            "features": [
                {
                    "featureType": "TEXT_EXTRACTION"
                }
            ],
            "isZipOutputEnabled": False
        },
        "compartmentId": compartmentId,
        "inputLocation": {
            "sourceType": "OBJECT_STORAGE_LOCATIONS",
            "objectLocations": [
                {
                    "bucketName": bucketName,
                    "namespaceName": namespace,
                    "objectName": resourceName
                }
            ]
        },
        "outputLocation": {
            "namespaceName": namespace,
            "bucketName": bucketName,
            "prefix": "document"
        }
    }
    resp = document_understanding_client.create_processor_job(job)
    log_in_file("documentUnderstanding_resp",str(resp.data))
    log( "</documentUnderstanding>")

## -- decodeJson ------------------------------------------------------------------

def decodeJson(value):
    log( "<decodeJson>")
    global signer
    fnOcid = os.getenv('FN_OCID')
    fnInvokeEndpoint = os.getenv('FN_INVOKE_ENDPOINT')
    namespace = value["data"]["additionalDetails"]["namespace"]
    bucketName = value["data"]["additionalDetails"]["bucketName"]
    resourceName = value["data"]["resourceName"]
    resourceId = value["data"]["resourceId"]
    
    # Read the JSON file from the object storage
    os_client = oci.object_storage.ObjectStorageClient(config = {}, signer=signer)
    resp = os_client.get_object(namespace_name=namespace, bucket_name=bucketName, object_name=resourceName)
    file_name = LOG_DIR+"/"+UNIQUE_ID+".json"
    with open(file_name, 'wb') as f:
        for chunk in resp.data.raw.stream(1024 * 1024, decode_content=False):
            f.write(chunk)

    with open(file_name, 'r') as f:
        file_content = f.read()
    log("Read file from object storage: "+ file_name)
    j = json.loads(file_content)   

    if resourceName[:resourceName.index("/")] == "document":
        # DocUnderstanding
        concat_text = ""
        pages = []
        for p in j.get("pages"):
            page = ""
            for l in p.get("lines"):
                page += l.get("text") + "\n"
            pages.append(page)
            concat_text += page + " "    
        original_resourcename = resourceName[:resourceName.index(".json")][resourceName.index("/results/")+9:]
        original_resourceid = "/n/" + namespace + "/b/" + bucketName + "/o/" + original_resourcename
        result = {
            "filename": original_resourcename,
            "date": UNIQUE_ID,
            "applicationName": "OCI Document Understanding",
            "modified": UNIQUE_ID,
            "contentType": j["documentMetadata"]["mimeType"],
            "creationDate": UNIQUE_ID,
            "content": concat_text,
            "pages": pages,
            "path": original_resourceid
        }
    else:
        # Speech
        original_resourcename = resourceName[:resourceName.index(".json")][resourceName.index("_"):]
        original_resourceid = "/n/" + namespace + "/b/" + bucketName + "/o/" + original_resourcename
        result = {
            "filename": original_resourcename,
            "date": UNIQUE_ID,
            "applicationName": "OCI Speech",
            "modified": UNIQUE_ID,
            "contentType": j["audioFormatDetails"]["format"],
            "creationDate": UNIQUE_ID,
            "content": j["transcriptions"][0]["transcription"],
            "path": original_resourceid
        }
    log( "</decodeJson>")
    return result
