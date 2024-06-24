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


## -- appendChunk -----------------------------------------------------------

def appendChunck(result, text, char_start, char_end ):
    chunck = text[char_start:char_end]
    result.append( { "chunck": chunck, "char_start": char_start, "char_end": char_end } )
    log("chunck (" + str(char_start) + "-" + str(char_end-1) + ") - " + chunck)      

## -- cutInChunks -----------------------------------------------------------

def cutInChunks(text):
    result = []
    prev = ""
    i = 0
    last_good_separator = 0
    last_medium_separator = 0
    last_bad_separator = 0
    MAXLEN = 250
    char_start = 0
    char_end = 0

    i = 0
    while i<len(text)-1:
        i += 1
        cur = text[i]
        cur2 = prev + cur
        prev = cur

        if cur2 in [ ". ", ".[" , ".\n", "\n\n" ]:
            last_good_separator = i
        if cur in [ "\n" ]:          
            last_medium_separator = i
        if cur in [ " " ]:          
            last_bad_separator = i
        # log( 'cur=' + cur + ' / cur2=' + cur2 )
        if i-char_start>MAXLEN:
            char_end = i
            if last_good_separator > 0:
               char_end = last_good_separator
            elif last_medium_separator > 0:
               char_end = last_medium_separator
            elif last_bad_separator > 0:
               char_end = last_bad_separator
            # XXXX
            if text[char_end] in [ "[", "(" ]:
                appendChunck( result, text, char_start, char_end )
            else:     
                appendChunck( result, text, char_start, char_end )
            char_start=char_end 
            last_good_separator = 0
            last_medium_separator = 0
            last_bad_separator = 0
    # Last chunck
    appendChunck( result, text, char_start, len(text) )

    # Overlapping chuncks
    if len(result)==1:
        return result
    else: 
        result2 = []
        s= ""
        chunck_count=0
        chunck_start=1
        for c in result:
            s = s+c["chunck"]
            chunck_count = chunck_count + 1
            if chunck_count==4:
                result2.append( { "chunck": s, "char_start": chunck_start, "char_end": c["char_end"] } )
                s = c["chunck"]
                chunck_start = c["char_start"]
                chunck_count = 0
        if chunck_count>0:
            result2.append( { "chunck": s, "char_start": chunck_start, "char_end": len(text) } )
        return result2

## -- embedText ------------------------------------------------------

# Ideally all vectors should be created in one call
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

def llama_chat2(prompt):
    global signer
    log( "<llama_chat2>")
    compartmentId = os.getenv("TF_VAR_compartment_ocid")
    endpoint = 'https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/20231130/actions/chat'
    #         "modelId": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyafhwal37hxwylnpbcncidimbwteff4xha77n5xz4m7p6a",
    #         "modelId": "cohere.command-r-16k",
    body = { 
        "compartmentId": compartmentId,
        "servingMode": {
            "modelId": "meta.llama-3-70b-instruct",
            "servingType": "ON_DEMAND"
        },
        "chatRequest": {
            "apiFormat": "GENERIC",
            "maxTokens": 600,
            "temperature": 0,
            "preambleOverride": "",
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "messages": [
                {
                    "role": "USER", 
                    "content": [
                        {
                            "type": "TEXT",
                            "text": prompt
                        }
                    ]
                }  
            ]
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
    log( "</llama_chat2>")
    return s

def llama_chat(messages):
    ## XXXX DOES NOT WORK XXXX ?
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
            "frequencyPenalty": 0,
            "presencePenalty": 0,
            "topP": 0.75,
            "topK": 0,
            "isStream": False,
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

def cohere_chat(prompt, chatHistory, documents):
    global signer
    log( "<cohere_chat>")

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
            "message": prompt,
            "chatHistory": chatHistory,
            "documents": documents,
            "apiFormat": "COHERE"
        }
    }
    log_in_file("cohere_chat_request", json.dumps(body)) 
    resp = requests.post(endpoint, json=body, auth=signer)
    resp.raise_for_status()
    log(resp)    
    # Binary string conversion to utf8
    log_in_file("cohere_chat_resp", resp.content.decode('utf-8'))
    j = json.loads(resp.content)   
    s = j["chatResponse"]
    log( "</cohere_chat>")
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
