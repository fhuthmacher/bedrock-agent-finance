import boto3
import time
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

agent_version = 'DRAFT'
bucket = 'bedrockfinance-databucket-bylcmdoiqlo0'
open_api_s3_url = 's3://' + bucket + '/code/agent_aws_openapi.json'

action_group_name = 'financetstgrp'
lambda_arn = 'arn:aws:lambda:us-east-1:026459568683:function:bedrockfinance-BedrockAgentToolsLambdaFunction-77I4yn5rpRCl'
agent_id= 'P6FNWDJIAM'


current_session = boto3.session.Session()
region = current_session.region_name
print(f"The current region is {region}")
#kb_collection_url = 'https://11v11bokow77rbguepqf.us-east-1.aoss.amazonaws.com:443/bedrock-kb-demo'
kb_collection_url = 'https://11v11bokow77rbguepqf.us-east-1.aoss.amazonaws.com'
bedrock_agent_client = boto3.client('bedrock-agent', region_name = region)

# set up Opensearch Serverless collection for KB
opensearch_hostname = kb_collection_url.replace("https://", "")

service = 'aoss'
credentials = current_session.get_credentials()

awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service,
session_token=credentials.token)

# Create an OpenSearch client
client = OpenSearch(
    hosts = [{'host': opensearch_hostname, 'port': 443}],
    http_auth = awsauth,
    timeout = 300,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)
index_name = "bedrock-kb-demo"
vector_field = "kb_vector"
text_field = "kb_text"
bedrock_metadata_field = "bedrock"
vector_size = 1536

index_found = False
try:
    client.indices.get(index=index_name)
    index_found = True
except:
    print("Index does not exist, create the index")

#create a new index
if index_found == False:
    index_body = {
        "settings": {
            "index.knn": True
        },
        'mappings': {
        'properties': {
            f"{vector_field}": { "type": "knn_vector", "dimension": vector_size, "method": {"engine": "nmslib", "space_type": "cosinesimil", "name": "hnsw", "parameters": {}   } },
            f"{text_field}": { "type": "text" },
            f"{bedrock_metadata_field}": { "type": "text", "index": False }
        }
        }
    }

    client.indices.create(
        index=index_name, 
        body=index_body
    )
    # wait 30 seconds for index creation to complete
    time.sleep(30)

client.indices.get(index=index_name)
