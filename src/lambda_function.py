import json
import requests
from requests.auth import HTTPBasicAuth
import boto3

# Define the DynamoDB table that Lambda will connect to
table_name = "AutoTradingTable"

# Create the DynamoDB resource
dynamo = boto3.resource('dynamodb').Table(table_name)

# Define some functions to perform the CRUD operations
def create(payload):
    return dynamo.put_item(Item=payload['Item'])

def read(payload):
    return dynamo.get_item(Key=payload['Key'])

def update(payload):
    return dynamo.update_item(**{k: payload[k] for k in ['Key', 'UpdateExpression', 
    'ExpressionAttributeNames', 'ExpressionAttributeValues'] if k in payload})

def delete(payload):
    return dynamo.delete_item(Key=payload['Key'])

def echo(payload):
    return payload

operations = {
    'create': create,
    'read': read,
    'update': update,
    'delete': delete,
    'echo': echo,
}

# Replace with actual OAuth2 credentials and token endpoint
OAUTH2_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token?client_id=1u7u5TtvW2F7JhRLqqAatWFLdRboGeuPA&redirect_uri=https://3oldess074.execute-api.us-east-1.amazonaws.com/Prod"
CLIENT_ID = "u7u5TtvW2F7JhRLqqAatWFLdRboGeuPA"
CLIENT_SECRET = "GOToxcsa1yxv6LCG"

# Replace with actual stock API URL
STOCK_API_URL = "https://api.schwabapi.com/trader/v1/accounts"

def get_oauth2_token():
    """ Fetch an OAuth2 token using client credentials grant. """
    response = requests.post(
        OAUTH2_TOKEN_URL,
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "client_credentials"}
    )
    print("response: ", response.json())
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to get token: {response.text}")

def fetch_stock_prices(tickers, access_token):
    """ Fetch stock prices from an external API using OAuth2 token. """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(STOCK_API_URL, json={"tickers": tickers}, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Oauth API Error: {response.text}")
    

def getAccountDetails(field, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"field": field}
    print("params: ", params)
    response = requests.get(STOCK_API_URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Stock API Error: {response.text}")

def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event["body"])
        # tickers = body.get("tickers", [])
        field = body.get("field")
        print("field: ", field)

        # if not tickers or not isinstance(tickers, list):
        #     return {
        #         "statusCode": 400,
        #         "body": json.dumps({"error": "Invalid input, provide a list of tickers."})
        #     }

        # Get OAuth2 token
        access_token = get_oauth2_token()

        # Fetch stock prices
        # stock_data = fetch_stock_prices(tickers, access_token)
        position_data = getAccountDetails(field, access_token)

        return {
            "statusCode": 200,
            "body": json.dumps(position_data)
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
