import boto3
import botocore
import json
import requests
import datetime as dt
import time
from decimal import Decimal

dynamo = boto3.resource('dynamodb')
b_table = dynamo.Table('tenant')

def default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError("Object of type '%s' is not JSON serializable" % type(obj).__name__)

def lambda_handler(event, context):
    # Scanning the table to retrieve items from DB
    response_scan = b_table.scan()
    for x in response_scan['Items']:
        current_time = dt.datetime.strptime(time.strftime("%m/%d/%y %H:%M:%S"), '%m/%d/%y %H:%M:%S')
        # print("DB Time: ", x['duration'])
        # print("Current Time: ", current_time)
        if str(current_time) >= x['duration']:
            print("Tenant Id: ", x['id'], " needs to be formatted")
            tenantId = x['id']
            # Retrieve Admin Users for a tenant
            print("Retrieving Admin Users for a tenant...")
            try:
                # Invoking the Auth URL
                print("Invoking the Auth URL...")

                authUrl = 'https://cloudinfra-gw.portal.checkpoint.com/auth/user'
                data = '{ "email": "demo-environment@checkpoint.com", "password": "Ly755900Ly755900!" }'

                authResponse = requests.post(authUrl, data=data,headers={"Content-Type": "application/json"})
                print("Auth Response: ", authResponse.text)
                csrf = authResponse.json()['csrf']
                print("Auth CSRF: ", csrf)
                
                # Invoking the Tenant URL
                print("Invoking the Tenant URL for tenant: ", tenantId)
                tenantUrl = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/auth/updateUserActiveTenant'
                headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': csrf}
                data = '{ "tenantId": "' + tenantId + '"}'
                
                tenantResponse = requests.put(tenantUrl, data=data, headers=headers, cookies=authResponse.cookies)
                print("Tenant Response: ", tenantResponse.text)
                tenantCSRF = tenantResponse.json()['csrf']
                print("Tenant CSRF: ", tenantCSRF)
                
                # Getting admins of tenant
                print("Retrieving admins of tenants...")
                retrieveAdminURL = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/user?limit=20'
                headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': tenantCSRF}
                
                adminsResponse = requests.get(retrieveAdminURL, headers=headers, cookies=tenantResponse.cookies)
                adminsResponseJSON = adminsResponse.json()
                adminsList = adminsResponseJSON["rows"]
                print("Admin List Type: ", type(adminsList))
                print("Admin List: ", adminsList)
                
                # Deleting an admin
                print("Deleting all admins of tenants...")

                for x in adminsList:
                    userId = x["id"]
                    deleteAdminURL = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/user?id=' + userId
                    headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': tenantCSRF}
                    adminsResponse = requests.delete(deleteAdminURL, headers=headers, cookies=tenantResponse.cookies)
                    print("Admin user ", userId, "deleted successfully!")

                # retrieveAdminURL = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/user?limit=20'
                # headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': tenantCSRF}
                
                # adminsResponse = requests.get(retrieveAdminURL, headers=headers, cookies=tenantResponse.cookies)
                # print("User Response: ", adminsResponse.text)

                # return {
                #         "message": adminsResponse.text
                #     }
            except Exception as e:
                print(e)
