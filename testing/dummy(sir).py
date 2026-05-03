import requests
import json

BASE_URL = "http://127.0.0.1:5000/"
token = None
created_user_id =None


def login_and_get_token():
    global token

    url = BASE_URL+"api/auth/login"
    payload = {"email":"admin@example.com",
               "password":"Admin@123"
               }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url,json=payload,headers=headers)

    data = response.json()
    token = data["access_token"]
    return token
login_and_get_token()


def get_auth_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

'''def test_get_user():
    url = BASE_URL+'api/users'
    response = requests.get(url,headers=get_auth_headers())
    print("\n GET USERS RESPONSE")
    print("\nSTATUS CODE: ", response.status_code)
    print("\n RESPONSE BODY:-", response.json())

    if response.status_code == 200:
        print("GET Request passed")
    else:
        print("Get Request failed")

test_get_user()'''


'''def test_post_user():
    global created_user_id
    url = BASE_URL+"api/users"
    payload = {
        "full_name":"Test User4",
        "email":"tesruser4@example.com",
        "password":"Password@123",
        "role":"Studnets",
        "is_active":True
    }

    response = requests.post(url,json=payload,headers=get_auth_headers())

    print("\n POST USER RESPONSE")
    print("\nSTATUS CODE: ", response.status_code)
    print("\n RESPONSE BODY:-", response.json())

    if response.status_code == 201:
        response_data = response.json()
        created_user_id=response_data['user']['id']
        print("POST Request passed")
        print("Created user id",created_user_id)
    else:
        print("POST request failed")

print(test_post_user())'''
