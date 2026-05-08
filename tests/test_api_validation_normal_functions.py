"""
Normal Python Function-Based API Validation
-------------------------------------------
No pytest.
No unittest.
No jsonschema.
Only basic Python functions + assert keyword.

Covered from api_validation_check.xlsx:
GET    -> status code, response body, schema, query param, empty data,
          DB validation, data count, response time, 429 rate-limit check.
POST   -> status code, request body, response body, mandatory fields,
          missing fields, duplicate data, invalid data type, boundary value,
          DB insertion, action log, response time, security/token testing.
PUT    -> status code, full payload required, existing record update,
          invalid ID, missing mandatory field, wrong data type, DB update,
          old values replaced, action log, response time.
PATCH  -> partial update, invalid ID, empty payload, wrong data type, DB update.
DELETE -> status code, response body, DB delete validation, data count change,
          invalid ID, action log, response time.
"""

import sqlite3
import time
from pathlib import Path

import requests


# CONFIGURATION
# =====================================================================
BASE_URL = "http://127.0.0.1:5000"
ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "app" / "instance" / "site.db"
MAX_RESPONSE_TIME_MS = 3000

HEADERS = {"Content-Type": "application/json"}
JWT_TOKEN = None
CREATED_USER_ID = None
UNIQUE_EMAIL = f"api_test_user_{int(time.time())}@example.com"
UPDATED_EMAIL = f"api_updated_user_{int(time.time())}@example.com"

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0


# =====================================================================
# BASIC TEST RUNNER - NO PYTEST / NO UNITTEST
# =====================================================================
def run_test(test_function):
    global TOTAL_TESTS, PASSED_TESTS, FAILED_TESTS
    TOTAL_TESTS += 1
    try:
        test_function()
        PASSED_TESTS += 1
        print(f"[PASS] {test_function.__name__}")
    except AssertionError as error:
        FAILED_TESTS += 1
        print(f"[FAIL] {test_function.__name__} -> {error}")
    except Exception as error:
        FAILED_TESTS += 1
        print(f"[ERROR] {test_function.__name__} -> {type(error).__name__}: {error}")


def print_summary():
    print("\n" + "=" * 90)
    print("FINAL TEST SUMMARY")
    print("=" * 90)
    print(f"Total Test Functions : {TOTAL_TESTS}")
    print(f"Passed Test Functions: {PASSED_TESTS}")
    print(f"Failed Test Functions: {FAILED_TESTS}")
    print("=" * 90)


# =====================================================================
# COMMON ASSERTION FUNCTIONS USING assert KEYWORD
# =====================================================================
def assert_status_code(response, expected_status_code):
    assert response.status_code == expected_status_code, (
        f"Expected status code {expected_status_code}, got {response.status_code}. "
        f"Response body: {response.text}"
    )


def assert_status_code_in(response, expected_status_codes):
    assert response.status_code in expected_status_codes, (
        f"Expected status code in {expected_status_codes}, got {response.status_code}. "
        f"Response body: {response.text}"
    )


def assert_response_time(response, max_ms=MAX_RESPONSE_TIME_MS):
    actual_ms = response.elapsed.total_seconds() * 1000
    assert actual_ms <= max_ms, f"Response time {actual_ms:.2f} ms exceeded SLA {max_ms} ms"


def assert_json_response(response):
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, f"Expected JSON response, got Content-Type: {content_type}"
    data = response.json()
    assert data is not None, "Response JSON body is empty"
    return data


def assert_required_keys(data, required_keys):
    for key in required_keys:
        assert key in data, f"Missing required response key: {key}. Actual data: {data}"


def assert_data_types(data, expected_types):
    for key, expected_type in expected_types.items():
        assert key in data, f"Missing key for type validation: {key}"
        assert isinstance(data[key], expected_type), (
            f"Invalid type for key '{key}'. Expected {expected_type.__name__}, "
            f"got {type(data[key]).__name__}. Value: {data[key]}"
        )


def assert_user_schema(user_data):
    expected_types = {
        "id": int,
        "full_name": str,
        "email": str,
        "role": str,
        "is_active": bool,
    }
    assert_required_keys(user_data, list(expected_types.keys()))
    assert_data_types(user_data, expected_types)


def assert_user_list_schema(users):
    assert isinstance(users, list), f"Expected list response, got {type(users).__name__}"
    for user in users:
        assert isinstance(user, dict), f"Every user item should be object/dict. Got: {user}"
        assert_user_schema(user)


def assert_error_response(response):
    data = assert_json_response(response)
    assert "error" in data, f"Error response must contain 'error' key. Actual: {data}"
    assert isinstance(data["error"], str), "Error message should be string"
    return data


def assert_request_body_has_required_fields(payload, required_fields):
    missing = [field for field in required_fields if field not in payload or payload.get(field) in (None, "")]
    assert len(missing) == 0, f"Request payload missing required fields: {missing}"


def assert_request_body_json_object(payload):
    assert isinstance(payload, dict), f"Request body should be JSON object/dict. Got: {type(payload).__name__}"


# =====================================================================
# DATABASE HELPER FUNCTIONS USING BASIC sqlite3
# =====================================================================
def open_db_connection():
    assert DB_PATH.exists(), f"Database file not found at {DB_PATH}. Start Flask app first."
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_user_from_db(user_id):
    connection = open_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, full_name, email, role, is_active FROM user WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
    }


def count_users_in_db():
    connection = open_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) AS user_count FROM user")
    row = cursor.fetchone()
    connection.close()
    return row["user_count"]


def table_exists(table_name):
    connection = open_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    row = cursor.fetchone()
    connection.close()
    return row is not None


def fetch_latest_action_log(action, resource_id):
    connection = open_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, action, http_method, resource_type, resource_id, endpoint, status_code
        FROM action_log
        WHERE action = ? AND resource_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (action, resource_id),
    )
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None


def assert_api_user_matches_db_user(api_user, db_user):
    assert db_user is not None, f"User not found in database. API user: {api_user}"
    assert api_user == db_user, f"API user and DB user mismatch. API={api_user}, DB={db_user}"


def assert_action_log_created(action, resource_id, expected_method):
    log = fetch_latest_action_log(action, resource_id)
    assert log is not None, f"Action log not found for action={action}, resource_id={resource_id}"
    assert log["action"] == action, f"Expected action {action}, got {log['action']}"
    assert log["http_method"] == expected_method, f"Expected method {expected_method}, got {log['http_method']}"
    assert log["resource_id"] == resource_id, f"Expected resource_id {resource_id}, got {log['resource_id']}"


# =====================================================================
# HTTP HELPER FUNCTIONS
# =====================================================================
def auth_headers():
    assert JWT_TOKEN is not None, "JWT token is not available. Login test must run first."
    headers = HEADERS.copy()
    headers["Authorization"] = f"Bearer {JWT_TOKEN}"
    return headers


def api_get(path, headers=None):
    return requests.get(f"{BASE_URL}{path}", headers=headers or auth_headers(), timeout=10)


def api_post(path, payload, headers=None):
    assert_request_body_json_object(payload)
    return requests.post(f"{BASE_URL}{path}", json=payload, headers=headers or auth_headers(), timeout=10)


def api_put(path, payload, headers=None):
    assert_request_body_json_object(payload)
    return requests.put(f"{BASE_URL}{path}", json=payload, headers=headers or auth_headers(), timeout=10)


def api_patch(path, payload, headers=None):
    assert_request_body_json_object(payload)
    return requests.patch(f"{BASE_URL}{path}", json=payload, headers=headers or auth_headers(), timeout=10)


def api_delete(path, headers=None):
    return requests.delete(f"{BASE_URL}{path}", headers=headers or auth_headers(), timeout=10)


# =====================================================================
# SERVER + AUTH TESTS
# =====================================================================
def test_001_server_health_check():
    response = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert_status_code(response, 200)
    assert_response_time(response)
    data = assert_json_response(response)
    assert_required_keys(data, ["status", "database", "message"])
    assert data["status"] == "up", f"Expected API status up, got {data['status']}"


def test_002_database_base_created():
    assert DB_PATH.exists(), f"SQLite DB should exist at {DB_PATH}"
    assert table_exists("user"), "user table should exist in DB"
    assert table_exists("action_log"), "action_log table should exist in DB"
    connection = open_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, email, role FROM user WHERE email = ?", ("admin@example.com",))
    admin = cursor.fetchone()
    connection.close()
    assert admin is not None, "Default admin user should be seeded in DB"
    assert admin["role"] == "admin", "Default admin role should be admin"


def test_003_get_users_without_jwt_token_security_check():
    response = requests.get(f"{BASE_URL}/api/users", timeout=10)
    assert_status_code(response, 401)
    assert_error_response(response)


def test_004_login_and_get_jwt_token():
    global JWT_TOKEN
    payload = {"email": "admin@example.com", "password": "Admin@123"}
    assert_request_body_has_required_fields(payload, ["email", "password"])

    response = requests.post(f"{BASE_URL}/api/auth/login", json=payload, headers=HEADERS, timeout=10)
    assert_status_code(response, 200)
    assert_response_time(response)

    data = assert_json_response(response)
    assert_required_keys(data, ["message", "access_token", "user"])
    assert isinstance(data["access_token"], str), "access_token should be string"
    assert len(data["access_token"]) > 20, "access_token length looks invalid"
    assert_user_schema(data["user"])

    JWT_TOKEN = data["access_token"]


def test_005_get_users_with_invalid_jwt_token_security_check():
    headers = HEADERS.copy()
    headers["Authorization"] = "Bearer invalid.token.value"
    response = requests.get(f"{BASE_URL}/api/users", headers=headers, timeout=10)
    assert_status_code_in(response, [401, 422])
    assert_error_response(response)


# =====================================================================
# POST VALIDATION TESTS
# =====================================================================
def test_006_post_create_user_success_status_body_schema_db_log():
    global CREATED_USER_ID
    payload = {
        "full_name": "API Test User",
        "email": UNIQUE_EMAIL,
        "password": "Password@123",
        "role": "student",
        "is_active": True,
    }
    assert_request_body_has_required_fields(payload, ["full_name", "email", "password"])

    response = api_post("/api/users", payload)
    assert_status_code(response, 201)
    assert_response_time(response)

    data = assert_json_response(response)
    assert_required_keys(data, ["message", "user"])
    assert_user_schema(data["user"])
    assert data["user"]["email"] == UNIQUE_EMAIL, "Created user email mismatch"

    CREATED_USER_ID = data["user"]["id"]
    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert_api_user_matches_db_user(data["user"], db_user)
    assert_action_log_created("CREATE", CREATED_USER_ID, "POST")


def test_007_post_missing_mandatory_fields_should_return_400():
    payload = {"full_name": "", "email": "", "password": ""}
    missing = [field for field in ["full_name", "email", "password"] if not payload.get(field)]
    assert len(missing) == 3, "Test data should intentionally contain missing mandatory fields"

    response = api_post("/api/users", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    error_data = assert_error_response(response)
    assert "details" in error_data, "Validation error should include details"


def test_008_post_duplicate_email_should_return_409():
    payload = {
        "full_name": "Duplicate User",
        "email": UNIQUE_EMAIL,
        "password": "Password@123",
        "role": "student",
        "is_active": True,
    }
    response = api_post("/api/users", payload)
    assert_status_code(response, 409)
    assert_response_time(response)
    assert_error_response(response)


def test_009_post_invalid_data_type_should_return_400():
    payload = {
        "full_name": ["Wrong", "Type"],
        "email": 12345,
        "password": 12345,
        "role": "student",
        "is_active": "true",
    }
    response = api_post("/api/users", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    error_data = assert_error_response(response)
    assert "details" in error_data, "Invalid type response should include details"


def test_010_post_boundary_value_should_return_400():
    payload = {
        "full_name": "A",  # less than minimum boundary 2
        "email": f"boundary_{int(time.time())}@example.com",
        "password": "123",  # less than minimum boundary 6
        "role": "x" * 51,   # greater than max boundary 50
        "is_active": True,
    }
    response = api_post("/api/users", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)


def test_011_post_sql_injection_payload_should_fail():
    payload = {
        "full_name": "Robert'); DROP TABLE user;--",
        "email": f"sql_{int(time.time())}@example.com",
        "password": "Password@123",
        "role": "student",
        "is_active": True,
    }
    response = api_post("/api/users", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)
    assert table_exists("user"), "Security validation failed: user table should still exist"


# =====================================================================
# GET VALIDATION TESTS
# =====================================================================
def test_012_get_all_users_status_body_schema_db_count():
    response = api_get("/api/users")
    assert_status_code(response, 200)
    assert_response_time(response)

    users = assert_json_response(response)
    assert_user_list_schema(users)

    api_count = len(users)
    db_count = count_users_in_db()
    assert api_count == db_count, f"API count {api_count} should match DB count {db_count}"


def test_013_get_single_user_status_body_schema_db_validation():
    response = api_get(f"/api/users/{CREATED_USER_ID}")
    assert_status_code(response, 200)
    assert_response_time(response)

    user = assert_json_response(response)
    assert_user_schema(user)

    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert_api_user_matches_db_user(user, db_user)


def test_014_get_query_parameter_id_validation():
    response = api_get(f"/api/users?id={CREATED_USER_ID}")
    assert_status_code(response, 200)
    assert_response_time(response)

    users = assert_json_response(response)
    assert_user_list_schema(users)
    assert len(users) == 1, f"Query parameter id should return exactly one user, got {len(users)}"
    assert users[0]["id"] == CREATED_USER_ID, "Query parameter id did not return correct user"


def test_015_get_empty_data_no_record_found():
    response = api_get("/api/users?id=99999999")
    assert_status_code(response, 200)
    assert_response_time(response)

    users = assert_json_response(response)
    assert isinstance(users, list), "Empty data response should still be a list"
    assert len(users) == 0, f"Expected empty list for no record found, got {users}"


def test_016_get_invalid_id_should_return_404():
    response = api_get("/api/users/99999999")
    assert_status_code(response, 404)
    assert_response_time(response)
    assert_error_response(response)


def test_017_get_rate_limit_should_return_429():
    status_codes = []
    for _ in range(5):
        response = api_get("/api/test/rate-limit-demo")
        status_codes.append(response.status_code)
    assert 429 in status_codes, f"Expected at least one 429 response, got status codes {status_codes}"


# =====================================================================
# PUT VALIDATION TESTS
# =====================================================================
def test_018_put_update_user_full_payload_status_db_old_values_log():
    old_db_user = fetch_user_from_db(CREATED_USER_ID)
    assert old_db_user is not None, "User should exist before PUT update"

    payload = {
        "full_name": "PUT Updated User",
        "email": UPDATED_EMAIL,
        "role": "mentor",
        "is_active": False,
        "password": "NewPassword@123",
    }
    assert_request_body_has_required_fields(payload, ["full_name", "email", "role", "is_active"])

    response = api_put(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 200)
    assert_response_time(response)

    data = assert_json_response(response)
    assert_required_keys(data, ["message", "user"])
    assert_user_schema(data["user"])

    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert_api_user_matches_db_user(data["user"], db_user)
    assert db_user["full_name"] != old_db_user["full_name"], "Old full_name should be replaced after PUT"
    assert db_user["email"] != old_db_user["email"], "Old email should be replaced after PUT"
    assert db_user["role"] == "mentor", "Role should be updated to mentor"
    assert db_user["is_active"] is False, "is_active should be updated to False"
    assert_action_log_created("UPDATE", CREATED_USER_ID, "PUT")


def test_019_put_missing_mandatory_field_should_return_400():
    payload = {
        "full_name": "Missing Role User",
        "email": f"missing_role_{int(time.time())}@example.com",
        # role missing intentionally
        "is_active": True,
    }
    response = api_put(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)


def test_020_put_invalid_id_should_return_404():
    payload = {
        "full_name": "Invalid Id User",
        "email": f"invalid_id_{int(time.time())}@example.com",
        "role": "student",
        "is_active": True,
    }
    response = api_put("/api/users/99999999", payload)
    assert_status_code(response, 404)
    assert_response_time(response)
    assert_error_response(response)


def test_021_put_wrong_data_type_should_return_400():
    payload = {
        "full_name": "Wrong Type User",
        "email": f"wrong_type_{int(time.time())}@example.com",
        "role": "student",
        "is_active": "false",  # wrong type intentionally
    }
    response = api_put(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)


# =====================================================================
# PATCH VALIDATION TESTS
# =====================================================================
def test_022_patch_partial_update_status_db_log():
    before_patch_user = fetch_user_from_db(CREATED_USER_ID)
    assert before_patch_user is not None, "User should exist before PATCH update"

    payload = {"full_name": "PATCH Updated Name"}
    response = api_patch(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 200)
    assert_response_time(response)

    data = assert_json_response(response)
    assert_required_keys(data, ["message", "user"])
    assert_user_schema(data["user"])

    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert_api_user_matches_db_user(data["user"], db_user)
    assert db_user["full_name"] == "PATCH Updated Name", "PATCH should update only full_name"
    assert db_user["email"] == before_patch_user["email"], "PATCH should not change email when email not passed"
    assert db_user["role"] == before_patch_user["role"], "PATCH should not change role when role not passed"
    assert_action_log_created("PATCH", CREATED_USER_ID, "PATCH")


def test_023_patch_empty_payload_should_return_400():
    payload = {}
    response = api_patch(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)


def test_024_patch_invalid_id_should_return_404():
    payload = {"full_name": "Invalid Patch User"}
    response = api_patch("/api/users/99999999", payload)
    assert_status_code(response, 404)
    assert_response_time(response)
    assert_error_response(response)


def test_025_patch_wrong_data_type_should_return_400():
    payload = {"is_active": "yes"}
    response = api_patch(f"/api/users/{CREATED_USER_ID}", payload)
    assert_status_code(response, 400)
    assert_response_time(response)
    assert_error_response(response)


# =====================================================================
# DELETE VALIDATION TESTS
# =====================================================================
def test_026_delete_user_status_body_db_count_log():
    before_delete_count = count_users_in_db()
    response = api_delete(f"/api/users/{CREATED_USER_ID}")
    assert_status_code(response, 200)
    assert_response_time(response)

    data = assert_json_response(response)
    assert_required_keys(data, ["message"])
    assert isinstance(data["message"], str), "DELETE message should be string"

    db_user = fetch_user_from_db(CREATED_USER_ID)
    assert db_user is None, f"Deleted user should not exist in DB. Found: {db_user}"

    after_delete_count = count_users_in_db()
    assert after_delete_count == before_delete_count - 1, (
        f"DB count should decrease by 1 after DELETE. Before={before_delete_count}, After={after_delete_count}"
    )
    assert_action_log_created("DELETE", CREATED_USER_ID, "DELETE")


def test_027_delete_invalid_id_should_return_404():
    response = api_delete("/api/users/99999999")
    assert_status_code(response, 404)
    assert_response_time(response)
    assert_error_response(response)


def test_028_delete_without_token_should_return_401():
    response = requests.delete(f"{BASE_URL}/api/users/99999999", timeout=10)
    assert_status_code(response, 401)
    assert_response_time(response)
    assert_error_response(response)


# =====================================================================
# MAIN EXECUTION ORDER
# =====================================================================
def run_all_tests():
    print("=" * 90)
    print("NORMAL PYTHON API VALIDATION - FUNCTION BASED - ASSERT KEYWORD ONLY")
    print("=" * 90)
    print(f"Base URL : {BASE_URL}")
    print(f"DB Path  : {DB_PATH}")
    print("=" * 90)

    test_functions = [
        test_001_server_health_check,
        test_002_database_base_created,
        test_003_get_users_without_jwt_token_security_check,
        test_004_login_and_get_jwt_token,
        test_005_get_users_with_invalid_jwt_token_security_check,
        test_006_post_create_user_success_status_body_schema_db_log,
        test_007_post_missing_mandatory_fields_should_return_400,
        test_008_post_duplicate_email_should_return_409,
        test_009_post_invalid_data_type_should_return_400,
        test_010_post_boundary_value_should_return_400,
        test_011_post_sql_injection_payload_should_fail,
        test_012_get_all_users_status_body_schema_db_count,
        test_013_get_single_user_status_body_schema_db_validation,
        test_014_get_query_parameter_id_validation,
        test_015_get_empty_data_no_record_found,
        test_016_get_invalid_id_should_return_404,
        test_017_get_rate_limit_should_return_429,
        test_018_put_update_user_full_payload_status_db_old_values_log,
        test_019_put_missing_mandatory_field_should_return_400,
        test_020_put_invalid_id_should_return_404,
        test_021_put_wrong_data_type_should_return_400,
        test_022_patch_partial_update_status_db_log,
        test_023_patch_empty_payload_should_return_400,
        test_024_patch_invalid_id_should_return_404,
        test_025_patch_wrong_data_type_should_return_400,
        test_026_delete_user_status_body_db_count_log,
        test_027_delete_invalid_id_should_return_404,
        test_028_delete_without_token_should_return_401,
    ]

    for test_function in test_functions:
        run_test(test_function)

    print_summary()

    assert FAILED_TESTS == 0, f"Some test functions failed. Failed count: {FAILED_TESTS}"


if __name__ == "__main__":
    run_all_tests()
