import urllib.parse
import pdfkit
import json 
import oci


def parse_sitemap(links_file):
  """
  Reads a file containing links, extracts full URIs from each link,
  and prints them with the ".pdf" extension. Handles potential issues
  like empty lines or non-standard URLs.

  Args:
      links_file (str): Path to the file containing links.
  """


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

  try:
    with open(links_file, 'r') as f:
      for line in f:
        line = line.strip()  # Remove leading/trailing whitespace

        # Handle empty lines gracefully
        if not line:
          continue

        # Extract full URI using URL parsing
        try:
          parsed_url = urllib.parse.urlparse(line)
          full_uri = urllib.parse.urlunparse(parsed_url)
        except ValueError:
          # If URL parsing fails, use the entire line as the full URI (fallback)
          full_uri = line

        # Print the filename with the ".pdf" extension
        pdf_path = full_uri
        last_char = pdf_path[-1:]
        if last_char == '/':
          pdf_path = pdf_path[:-1]
        pdf_path = pdf_path.replace('https://', '');
        pdf_path = pdf_path.replace('/', '_');
        pdf_path = pdf_path.replace('.', '_');
        pdf_path = pdf_path.replace('-', '_');
        pdf_path = pdf_path+'.pdf'
        print(f"{full_uri}")
        pdfkit.from_url(full_uri, pdf_path)
        print(f"{pdf_path} created")
  

  except FileNotFoundError as e:
    print(f"Error: File '{links_file}' not found.")
  except Exception as e:
    print(f"An unexpected error occurred: {e}")

# Example usage
links_file = "links.txt"  # Replace with your actual file path
process_links(links_file)
