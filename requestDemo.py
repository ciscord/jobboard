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
    email = event.get('email', '') # Mandatory
    firstName = event.get('firstName', '')
    lastName = event.get('lastName', '')
    duration = event.get('duration', 0)

    if email == '':
        return {"statusCode": 500,
                "message": "Error: Please provide the user email!"
                }
    elif duration == '':
        return {"statusCode": 500,
                "message": "Error: Please provide a duration (in number)!"
                }
    else:
        try:
            response = b_table.scan()

            # Checking if a Tenant is free
            tenantId = ""
            for x in response['Items']:
                if x['status'] == "Free":
                    tenantId = x['id']
                    break
            
            print("Tenant Id: ", tenantId)
            
            # Update the table if an account is available
            if not tenantId == "":
                current_time = dt.datetime.strptime(time.strftime("%m/%d/%y %H:%M:%S"), '%m/%d/%y %H:%M:%S')
                print(current_time)
                new_time = current_time + dt.timedelta(hours=duration)
                print(new_time)
                response = b_table.update_item(
                    Key={'id': tenantId},
                    UpdateExpression='SET #attr1 = :val1, #attr2 = :val2, #attr3 = :val3, #attr4 = :val4, #attr5 = :val5',
                    ConditionExpression=(
                            'id = :tenantId'
                    ),
                    ExpressionAttributeNames={'#attr1': 'email', '#attr2': 'firstname', '#attr3': 'lastname', '#attr4': 'status', '#attr5': 'duration'},
                    ExpressionAttributeValues={':tenantId': tenantId, ':val1': email, ':val2': firstName, ':val3': lastName, ':val4': 'Occupied', ':val5': str(new_time)},
                    ReturnValues='ALL_NEW'
                )
                
                print("DB updated successfully with user details and duration")
            
                # Add User to an account
                print("Adding the user to an Account...")
                try:
                    # Invoking the Auth URL
                    print("Invoking the Auth URL...")

                    authUrl = 'https://cloudinfra-gw.portal.checkpoint.com/auth/user'
                    data = '{ "email": "demo-environment@checkpoint.com", "password": "xxxxxxx!" }'

                    authResponse = requests.post(authUrl, data=data,headers={"Content-Type": "application/json"})
                    print("Auth Response: ", authResponse.text)
                    csrf = authResponse.json()['csrf']
                    print("Auth CSRF: ", csrf)
                    
                    # Invoking the Tenant URL
                    print("Invoking the Tenant URL...")
                    tenantUrl = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/auth/updateUserActiveTenant'
                    headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': csrf}
                    data = '{ "tenantId": "' + tenantId + '"}'
                    
                    tenantResponse = requests.put(tenantUrl, data=data, headers=headers, cookies=authResponse.cookies)
                    print("Tenant Response: ", tenantResponse.text)
                    tenantCSRF = tenantResponse.json()['csrf']
                    print("Tenant CSRF: ", tenantCSRF)
                    
                    # Adding a User
                    print("Adding a user...")
                    addUserURL = 'https://cloudinfra-gw.portal.checkpoint.com/api/v1/user'
                    headers = { 'Content-Type': 'application/json', 'X-ACCESS-TOKEN': tenantCSRF}
                    data = '{ "name": "' + firstName + ' ' + lastName + '", "email": "' + email + '", "role": "admin" }'
                    
                    userResponse = requests.post(addUserURL, data=data, headers=headers, cookies=tenantResponse.cookies)
                    print("User Response: ", userResponse.text)
                
                    return {
                            "message": "User added Successfully in Account: " + tenantId
                        }
                except Exception as e:
                    print(e)
            # If account is not available
            else:
                return {
                        "message": "No Available Accounts!"
                    }
        except Exception as e:
            print(e)
    