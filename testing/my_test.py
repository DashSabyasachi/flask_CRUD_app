import requests

BASE_URL = "http://127.0.0.1:5000/"
token = None
created_user_id = None



def login_and_get_token():
    global token

    url = BASE_URL + "api/auth/login"
    payload = {
        "email": "admin@example.com",
        "password": "Admin@123"
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    token = data["access_token"]
    print(f" LOGIN SUCCESS | Status: {response.status_code}")
    print(f"   Token: {token[:40]}...")
    return token


def auth_headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }



def get_all_users():
    url = BASE_URL + "api/users"
    response = requests.get(url, headers=auth_headers())
    print(f"\n GET ALL USERS | Status: {response.status_code}")
    for user in response.json():
        print(f"   ID: {user['id']} | Name: {user['full_name']} | Email: {user['email']} | Role: {user['role']}")



def get_single_user(user_id):
    url = BASE_URL + f"api/users/{user_id}"
    response = requests.get(url, headers=auth_headers())
    data = response.json()
    print(f"\n GET SINGLE USER | Status: {response.status_code}")
    print(f"   ID: {data['id']} | Name: {data['full_name']} | Email: {data['email']}")



def create_user():
    global created_user_id

    url = BASE_URL + "api/users"
    payload = {
        "full_name": "Test User",
        "email": "testuser@gmail.com",
        "password": "Test@123",
        "role": "user"
    }
    response = requests.post(url, json=payload, headers=auth_headers())
    data = response.json()
    created_user_id = data["user"]["id"]
    print(f"\n CREATE USER | Status: {response.status_code}")
    print(f"   Created → ID: {created_user_id} | Name: {data['user']['full_name']} | Email: {data['user']['email']}")


def update_user_put(user_id):
    url = BASE_URL + f"api/users/{user_id}"
    payload = {
        "full_name": "Test User Updated",
        "email": "testupdated@gmail.com",
        "role": "user",
        "is_active": True
    }
    response = requests.put(url, json=payload, headers=auth_headers())
    data = response.json()
    print(f"\n PUT UPDATE USER | Status: {response.status_code}")
    print(f"   Updated → Name: {data['user']['full_name']} | Email: {data['user']['email']}")



def update_user_patch(user_id):
    url = BASE_URL + f"api/users/{user_id}"
    payload = {
        "full_name": "Test User Patched"
    }
    response = requests.patch(url, json=payload, headers=auth_headers())
    data = response.json()
    print(f"\n PATCH UPDATE USER | Status: {response.status_code}")
    print(f"   Patched → Name: {data['user']['full_name']}")



def delete_user(user_id):
    url = BASE_URL + f"api/users/{user_id}"
    response = requests.delete(url, headers=auth_headers())
    data = response.json()
    print(f"\n DELETE USER | Status: {response.status_code}")
    print(f"   {data['message']}")



login_and_get_token()
get_all_users()
get_single_user(1)
create_user()
update_user_put(created_user_id)
update_user_patch(created_user_id)
delete_user(created_user_id)

