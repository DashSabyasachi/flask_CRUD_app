import requests

BASE_URL = "http://127.0.0.1:5000/"
token = None
created_user_id = None


def login_and_get_token():
    global token

    url = BASE_URL+"api/auth/login"
    payload = {
        "email":"admin@example.com",
        "password":"Admin@123"
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url,json=payload,headers=headers)
    data = response.json()
    token = data["access_token"]
    return token
print(login_and_get_token())