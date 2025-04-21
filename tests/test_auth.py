from fastapi.testclient import TestClient
from app.main import app
from app.auth.auth import create_access_token, decode_access_token
from tests.test_db import override_get_db # Testing on sqlite

client = TestClient(app)

# Test signup and login
def test_signup_and_login():
    username = "testuser1"
    password = "testpass1"
  
    # Signup
    response = client.post("/signup", json={"username": username, "password": password})
    # Create user if not exists
    assert response.status_code == 200 or response.status_code == 400

    response = client.post("/login", json={"username": username, "password": password})
    assert response.status_code == 200
    data = response.json()
    # Check token exists
    assert "access_token" in data

# Test login failure - wrong password
def test_login_invalid_password():
    # testuser1 created in previous test
    response = client.post("/login", json={"username":"testuser1", "password":"wrongpass1"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"

# Test signup with username that already exists
def test_duplicate_signup():
    # testuser1 already exists
    response = client.post("/signup", json={"username": "testuser1", "password":"randompw"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"

# Test token create and decode
def test_token_create_and_decode():
    username = "testuser"
    token = create_access_token({"sub": username})
    decoded_username = decode_access_token(token)
    assert decoded_username == username
