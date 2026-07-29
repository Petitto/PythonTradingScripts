import json
import os
import requests
from requests.auth import HTTPBasicAuth
import boto3

# Define the DynamoDB table that Lambda will connect to
table_name = os.getenv("DYNAMODB_TABLE_NAME", "AutoTradingTable")

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

# Runtime configuration should come from environment variables in Lambda.
OAUTH2_TOKEN_URL = os.getenv("SCHWAB_OAUTH2_TOKEN_URL", "https://api.schwabapi.com/v1/oauth/token")
STOCK_API_URL = os.getenv("SCHWAB_STOCK_API_URL", "https://api.schwabapi.com/trader/v1/accounts")


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_oauth2_token():
    """Fetch an OAuth2 token using client credentials grant."""
    client_id = get_required_env("SCHWAB_CLIENT_ID")
    client_secret = get_required_env("SCHWAB_CLIENT_SECRET")

    response = requests.post(
        OAUTH2_TOKEN_URL,
        auth=HTTPBasicAuth(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=30,
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
    

def get_account_details(field, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"field": field}
    print("params: ", params)
    response = requests.get(STOCK_API_URL, headers=headers, params=params, timeout=30)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Stock API Error: {response.text}")

def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
        field = body.get("fields")

        # if not tickers or not isinstance(tickers, list):
        #     return {
        #         "statusCode": 400,
        #         "body": json.dumps({"error": "Invalid input, provide a list of tickers."})
        #     }

        # Get OAuth2 token
        access_token = get_oauth2_token()

        # Fetch stock prices
        # stock_data = fetch_stock_prices(tickers, access_token)
        position_data = get_account_details(field, access_token)

        return {
            "statusCode": 200,
            "body": json.dumps(position_data)
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
