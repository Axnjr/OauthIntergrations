# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import os
import requests
from kombu.utils.url import safequote
# from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# Couldn’t complete the connection Authorization failed because one or more scopes are invalid: contacts. Please contact the app developer.

CLIENT_ID = safequote(os.environ.get('HUBSPOT_CLIENT_ID', '000'))
CLIENT_SECRET = safequote(os.environ.get('HUBSPOT_CLIENT_SECRET', '000'))

# SECURITY
if(CLIENT_ID == "000" or CLIENT_SECRET == "000"):
    raise Exception("\n Hubspot 'CLIENT_ID' & 'CLIENT_SECRET' Not Found !!")

REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
scope = "crm.objects.contacts.read%20crm.objects.contacts.write"
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&scope={scope}&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fintegrations%2Fhubspot%2Foauth2callback'


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id,
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'


async def oauth2callback_hubspot(request: Request):

    print("\n HUBSPOT OAUTH CALLBACK HANDLER !! \n")

    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    
    code = request.query_params.get('code')

    # From hubspot documentation: 
    # `&state=y` If this parameter is included in the authorization URL, the value will be included in a state query parameter when 
    # the user is directed to the redirect_url. 👇

    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')
    
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                }, 
                headers={
                    # 'Authorization': f'Basic {encoded_client_id_secret}',
                    'Content-Type': 'application/x-www-form-urlencoded', #'application/json', # x-www-form-urlencoded
                }
            ),
        delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
    )

    print("\n DATA FROM HUBSPOT PROVIDER STORED IN REDIS SERVER !! \n")

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id, org_id):

    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')

    if not credentials:
        print("\n NO CREDENTIALS FOUND 1 \n")
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    credentials = json.loads(credentials)

    if not credentials:
        print("\n NO CREDENTIALS FOUND 2 \n")
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials


# from notion.py
async def create_integration_item_metadata_object(contact):
    properties = contact.get('properties', {})
    return {
        'id': contact.get('id'),
        'email': properties.get('email'),
        'firstname': properties.get('firstname'),
        'lastname': properties.get('lastname'),
        'createdate': properties.get('createdate'),
        'lastmodifieddate': properties.get('lastmodifieddate'),
    }


async def get_items_hubspot(credentials):

    # Aggregates all metadata relevant for a notion integration

    credentials = json.loads(credentials)

    response = requests.get(
        'https://api.hubapi.com/crm/v3/objects/contacts',
        headers={
            'Authorization': f'Bearer {credentials.get("access_token")}',
            'Content-Type': 'application/json'
        },
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch data from HubSpot: {response.status_code}, {response.text}")

    # Parse the response JSON
    data = response.json()
    # print("HubSpot API Response:", data)  # Debugging output

    results = data.get('results', [])
    if not results:
        print("No results found in HubSpot response.")
        return []

    list_of_integration_item_metadata = []

    # Process each result
    for result in results:
        try:
            integration_item = await create_integration_item_metadata_object(result)
            list_of_integration_item_metadata.append(integration_item)
        except Exception as e:
            print(f"Error processing result {result}: {e}")
            continue

    print("Processed Integration Items:", list_of_integration_item_metadata)
    return list_of_integration_item_metadata