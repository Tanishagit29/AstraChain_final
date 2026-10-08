def test_register_and_login(client):
    register_res = client.post(
        "/api/auth/register",
        json={
            "email": "testuser@astrachain.ai",
            "password": "SecretPassword123!",
            "full_name": "Test Operator",
            "role": "OPERATIONS_LEAD"
        }
    )
    assert register_res.status_code in [201, 200]
    data = register_res.json()
    assert data["success"] is True
    assert data["data"]["email"] == "testuser@astrachain.ai"

    login_res = client.post(
        "/api/auth/login",
        json={
            "email": "testuser@astrachain.ai",
            "password": "SecretPassword123!"
        }
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["success"] is True
    assert "access_token" in token_data["data"]
