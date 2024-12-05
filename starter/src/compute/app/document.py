from shared_oci import log
from shared_oci import log_in_file
import shared_db
import shared_oci
import pathlib

## -- insertDocument --------------------------------------------------------

def insertDocument(value):
    resourceName = value["data"]["resourceName"]
    lowerResourceName = resourceName.lower()
    resourceExtension = pathlib.Path(lowerResourceName).suffix
    log( "Extension:" + resourceExtension )
     
    # Content 
    result = { "content": "-" }
    if resourceName.startswith("belgian"):
        result = shared_oci.belgian(value)
    elif resourceExtension in [".png", ".jpg", ".jpeg", ".gif"]:
        result = shared_oci.vision(value)
    elif resourceExtension in [".srt"]:
        log("IGNORE .srt")
        return
    elif resourceExtension in [".json"]:
        result = shared_oci.decodeJson(value)
    elif resourceExtension in [".mp3", ".mp4", ".avi", ".wav", ".m4a"]:
        # This will create a SRT file in Object Storage that will create a second even with resourceExtension ".srt" 
        shared_oci.speech(value)
        return
    elif resourceExtension in [".tif",".pdf"]:
        # This will create a JSON file in Object Storage that will create a second even with resourceExtension "json" 
        shared_oci.documentUnderstanding(value)
        return
    elif resourceExtension in [".sitemap"]:
        # This will create a PDFs file in Object Storage with the content of each site (line) ".sitemap" 
        shared_oci.sitemap(value)
        return

    elif resourceName.endswith("/"):
        # Ignore
        log("IGNORE /")
        return
    else:
        result = shared_oci.invokeTika(value)

    log_in_file("content", result["content"])
    if len(result["content"])==0:
       return 
    
    result["source_type"] = "OBJECT_STORAGE"

    # Summary 
    if len(result["content"])>250:
        result["summary"] = shared_oci.summarizeContent(value, result["content"])
    else:    
        result["summary"] = result["content"]
    
    # Delete Document in repository
    deleteDocument( result["path"] )

    # If no page, just add the content
    if result.get("pages") == None:
        result["pages"] = { "1": result["content"] }

    shared_db.createDoc(result)        
                
## -- deleteDocument --------------------------------------------------------

def deleteDocument(resourceId):
    log( "<deleteDocument>")
    shared_db.deleteDoc(resourceId)
    log( "</deleteDocument>")