import json
import sqlite3
import time
from pathlib import Path

import requests
from jsonschema import validate
from jsonschema.exceptions import ValidationError

BASE_URL = 'http://127.0.0.1:5000'
DB_PATH = Path(__file__).resolve().parents[1] / 'app' / 'instance' / 'site.db'
MAX_RESPONSE_TIME_MS = 3000

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0
JWT_TOKEN = None
CREATED_USER_ID = None
HEADERS = {'Content-Type': 'application/json'}


# ============================================================
# COMMON RESULT / ASSERTION FUNCTIONS
# ============================================================
def print_result(test_name, passed, details=''):
    global TOTAL_TESTS, PASSED_TESTS, FAILED_TESTS
    TOTAL_TESTS += 1

    if passed:
        PASSED_TESTS += 1
        print(f'[PASS] {test_name}')
    else:
        FAILED_TESTS += 1
        print(f'[FAIL] {test_name} --> {details}')


def assert_true(condition, test_name, details=''):
    print_result(test_name, bool(condition), details)


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================
def validate_status_code(response, expected_code, test_name):
    actual_code = response.status_code
    assert_true(
        actual_code == expected_code,
        test_name,
        f'Expected {expected_code}, got {actual_code}, body={response.text}'
    )


def validate_response_time(response, test_name):
    response_time_ms = response.elapsed.total_seconds() * 1000
    assert_true(
        response_time_ms <= MAX_RESPONSE_TIME_MS,
        test_name,
        f'Response time {response_time_ms:.2f} ms exceeded {MAX_RESPONSE_TIME_MS} ms'
    )


def validate_json_key(data, key, test_name):
    assert_true(key in data, test_name, f'Missing key: {key}')


def validate_schema(data, schema, test_name):
    try:
        validate(instance=data, schema=schema)
        print_result(test_name, True)
    except ValidationError as exc:
        print_result(test_name, False, str(exc))


def validate_required_fields(payload, required_fields, test_name):
    missing_fields = [field for field in required_fields if not payload.get(field)]
    assert_true(
        len(missing_fields) == 0,
        test_name,
        f'Missing fields in request body: {missing_fields}'
    )


# ============================================================
# DATABASE FUNCTIONS
# ============================================================
def fetch_user_from_db(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, full_name, email, role, is_active FROM user WHERE id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None



def normalize_db_user(db_user):
    if db_user is None:
        return None

    return {
        'id': db_user['id'],
        'full_name': db_user['full_name'],
        'email': db_user['email'],
        'role': db_user['role'],
        'is_active': bool(db_user['is_active']),
    }



def compare_api_with_db(api_user, db_user, test_name):
    if db_user is None:
        print_result(test_name, False, 'No record found in database')
        return

    normalized_db = normalize_db_user(db_user)
    assert_true(api_user == normalized_db, test_name, f'API={api_user}, DB={normalized_db}')


# ============================================================
# AUTHENTICATION / JWT FUNCTIONS
# ============================================================
def login_and_get_jwt_token():
    global JWT_TOKEN, HEADERS

    payload = {
        'email': 'admin@example.com',
        'password': 'Admin@123'
    }

    response = requests.post(
        f'{BASE_URL}/api/auth/login',
        headers=HEADERS,
        data=json.dumps(payload)
    )

    validate_status_code(response, 200, 'JWT login status code validation')
    validate_response_time(response, 'JWT login response time validation')

    data = response.json()
    validate_json_key(data, 'access_token', 'JWT login response body contains access_token')
    validate_json_key(data, 'user', 'JWT login response body contains user')

    login_schema = {
        'type': 'object',
        'properties': {
            'message': {'type': 'string'},
            'access_token': {'type': 'string'},
            'user': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'full_name': {'type': 'string'},
                    'email': {'type': 'string'},
                    'role': {'type': 'string'},
                    'is_active': {'type': 'boolean'}
                },
                'required': ['id', 'full_name', 'email', 'role', 'is_active']
            }
        },
        'required': ['message', 'access_token', 'user']
    }
    validate_schema(data, login_schema, 'JWT login schema validation')

    JWT_TOKEN = data['access_token']
    HEADERS['Authorization'] = f'Bearer {JWT_TOKEN}'

    assert_true(bool(JWT_TOKEN), 'JWT token generation validation', 'Token is empty or missing')



def test_get_users_without_token():
    response = requests.get(f'{BASE_URL}/api/users')
    validate_status_code(response, 401, 'GET users without JWT token validation')


# ============================================================
# POST TEST SECTION
# ============================================================
def test_post_create_user():
    global CREATED_USER_ID

    payload = {
        'full_name': 'Test User One',
        'email': 'testuser1@example.com',
        'password': 'Password@123',
        'role': 'student',
        'is_active': True
    }

    validate_required_fields(
        payload,
        ['full_name', 'email', 'password'],
        'POST request body validation'
    )

    response = requests.post(
        f'{BASE_URL}/api/users',
        headers=HEADERS,
        data=json.dumps(payload)
    )

    validate_status_code(response, 201, 'POST create user status code validation')
    validate_response_time(response, 'POST create user response time validation')

    data = response.json()
    validate_json_key(data, 'message', 'POST create user response body contains message')
    validate_json_key(data, 'user', 'POST create user response body contains user')

    create_schema = {
        'type': 'object',
        'properties': {
            'message': {'type': 'string'},
            'user': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'full_name': {'type': 'string'},
                    'email': {'type': 'string'},
                    'role': {'type': 'string'},
                    'is_active': {'type': 'boolean'}
                },
                'required': ['id', 'full_name', 'email', 'role', 'is_active']
            }
        },
        'required': ['message', 'user']
    }
    validate_schema(data, create_schema, 'POST create user schema validation')

    CREATED_USER_ID = data['user']['id']
    db_user = fetch_user_from_db(CREATED_USER_ID)
    compare_api_with_db(data['user'], db_user, 'POST API vs database data comparison')


# ============================================================
# GET TEST SECTION
# ============================================================
def test_get_single_user():
    response = requests.get(f'{BASE_URL}/api/users/{CREATED_USER_ID}', headers=HEADERS)
    validate_status_code(response, 200, 'GET single user status code validation')
    validate_response_time(response, 'GET single user response time validation')

    data = response.json()
    user_schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer'},
            'full_name': {'type': 'string'},
            'email': {'type': 'string'},
            'role': {'type': 'string'},
            'is_active': {'type': 'boolean'}
        },
        'required': ['id', 'full_name', 'email', 'role', 'is_active']
    }
    validate_schema(data, user_schema, 'GET single user schema validation')

    db_user = fetch_user_from_db(CREATED_USER_ID)
    compare_api_with_db(data, db_user, 'GET API vs database data comparison')



def test_get_all_users():
    response = requests.get(f'{BASE_URL}/api/users', headers=HEADERS)
    validate_status_code(response, 200, 'GET all users status code validation')
    validate_response_time(response, 'GET all users response time validation')

    data = response.json()
    assert_true(isinstance(data, list), 'GET all users response body validation', 'Response is not a list')

    if data:
        list_schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'full_name': {'type': 'string'},
                    'email': {'type': 'string'},
                    'role': {'type': 'string'},
                    'is_active': {'type': 'boolean'}
                },
                'required': ['id', 'full_name', 'email', 'role', 'is_active']
            }
        }
        validate_schema(data, list_schema, 'GET all users schema validation')


# ============================================================
# PUT TEST SECTION
# ============================================================
def test_put_update_user():
    payload = {
        'full_name': 'Updated Test User',
        'email': 'updateduser@example.com',
        'role': 'mentor',
        'is_active': False,
        'password': 'NewPassword@123'
    }

    missing_fields = [field for field in ['full_name', 'email', 'role', 'is_active'] if field not in payload]
    assert_true(
        len(missing_fields) == 0,
        'PUT request body validation',
        f'Missing fields in request body: {missing_fields}'
    )

    response = requests.put(
        f'{BASE_URL}/api/users/{CREATED_USER_ID}',
        headers=HEADERS,
        data=json.dumps(payload)
    )

    validate_status_code(response, 200, 'PUT update user status code validation')
    validate_response_time(response, 'PUT update user response time validation')

    data = response.json()
    validate_json_key(data, 'user', 'PUT response body contains user')

    db_user = fetch_user_from_db(CREATED_USER_ID)
    compare_api_with_db(data['user'], db_user, 'PUT API vs database data comparison')


# ============================================================
# PATCH TEST SECTION
# ============================================================
def test_patch_update_user():
    payload = {
        'full_name': 'Patched User Name'
    }

    assert_true('full_name' in payload, 'PATCH request body validation', 'PATCH payload is empty')

    response = requests.patch(
        f'{BASE_URL}/api/users/{CREATED_USER_ID}',
        headers=HEADERS,
        data=json.dumps(payload)
    )

    validate_status_code(response, 200, 'PATCH update user status code validation')
    validate_response_time(response, 'PATCH update user response time validation')

    data = response.json()
    validate_json_key(data, 'user', 'PATCH response body contains user')

    db_user = fetch_user_from_db(CREATED_USER_ID)
    compare_api_with_db(data['user'], db_user, 'PATCH API vs database data comparison')


# ============================================================
# NEGATIVE VALIDATION SECTION
# ============================================================
def test_negative_request_body_validation():
    payload = {
        'full_name': '',
        'email': '',
        'password': ''
    }

    missing_fields = [field for field in ['full_name', 'email', 'password'] if not payload.get(field)]
    assert_true(
        len(missing_fields) == 3,
        'Negative request body validation',
        f'Expected 3 missing fields, got {missing_fields}'
    )

    response = requests.post(
        f'{BASE_URL}/api/users',
        headers=HEADERS,
        data=json.dumps(payload)
    )

    validate_status_code(response, 400, 'Negative POST missing fields status code validation')
    data = response.json()
    validate_json_key(data, 'error', 'Negative POST response body contains error')


# ============================================================
# DELETE TEST SECTION
# ============================================================
def test_delete_user():
    response = requests.delete(f'{BASE_URL}/api/users/{CREATED_USER_ID}', headers=HEADERS)
    validate_status_code(response, 200, 'DELETE user status code validation')
    validate_response_time(response, 'DELETE user response time validation')

    data = response.json()
    validate_json_key(data, 'message', 'DELETE response body validation')

    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert_true(db_user is None, 'DELETE database validation after deletion', f'Record still exists in DB: {db_user}')


# ============================================================
# RUNNER SECTION
# ============================================================
def print_header():
    print('=' * 80)
    print('STARTING NORMAL PYTHON API AUTOMATION TESTING - FUNCTION BASED')
    print('=' * 80)
    print(f'Expected database path: {DB_PATH}')
    if not DB_PATH.exists():
        print('[WARNING] Database file not found. Start the Flask app once before running tests.')



def print_summary():
    print('\n' + '=' * 80)
    print('FINAL TEST SUMMARY')
    print('=' * 80)
    print(f'Total Tests   : {TOTAL_TESTS}')
    print(f'Passed Tests  : {PASSED_TESTS}')
    print(f'Failed Tests  : {FAILED_TESTS}')
    print('=' * 80)



def run_all_tests():
    print_header()
    test_get_users_without_token()
    login_and_get_jwt_token()
    test_post_create_user()
    test_get_single_user()
    test_put_update_user()
    test_patch_update_user()
    test_get_all_users()
    test_negative_request_body_validation()
    test_delete_user()
    print_summary()


if __name__ == '__main__':
    time.sleep(1)
    run_all_tests()
