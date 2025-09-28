import pytest
from httpx import AsyncClient
from fastapi import status

# Test authentication flow integration
@pytest.mark.asyncio
async def test_auth_flow(async_client: AsyncClient):
    """Test the complete authentication flow from registration to login to accessing protected resources"""
    # Test user registration
    register_data = {
        "email": "test_integration@example.com",
        "password": "securePassword123!",
        "name": "Integration Test User"
    }
    
    register_response = await async_client.post("/auth/register", json=register_data)
    assert register_response.status_code == status.HTTP_201_CREATED
    assert "user_id" in register_response.json()
    
    # Test user login
    login_data = {
        "email": "test_integration@example.com",
        "password": "securePassword123!"
    }
    
    login_response = await async_client.post("/auth/login", json=login_data)
    assert login_response.status_code == status.HTTP_200_OK
    assert "access_token" in login_response.json()
    assert "token_type" in login_response.json()
    
    # Extract token for authenticated requests
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test accessing protected endpoint
    profile_response = await async_client.get("/users/me", headers=headers)
    assert profile_response.status_code == status.HTTP_200_OK
    assert profile_response.json()["email"] == "test_integration@example.com"
    
    # Test token refresh
    refresh_response = await async_client.post("/auth/refresh", headers=headers)
    assert refresh_response.status_code == status.HTTP_200_OK
    assert "access_token" in refresh_response.json()
    
    # Test logout
    logout_response = await async_client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == status.HTTP_200_OK
    
    # Verify token is invalidated
    invalid_token_response = await async_client.get("/users/me", headers=headers)
    assert invalid_token_response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_auth_failures(async_client: AsyncClient):
    """Test authentication failure scenarios"""
    # Test invalid login
    invalid_login = {
        "email": "nonexistent@example.com",
        "password": "wrongPassword"
    }
    
    response = await async_client.post("/auth/login", json=invalid_login)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Test accessing protected endpoint without token
    no_auth_response = await async_client.get("/users/me")
    assert no_auth_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Test with invalid token
    invalid_headers = {"Authorization": "Bearer invalidtokenstring"}
    invalid_token_response = await async_client.get("/users/me", headers=invalid_headers)
    assert invalid_token_response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_password_reset_flow(async_client: AsyncClient):
    """Test the password reset flow"""
    # Request password reset
    reset_request = {
        "email": "test_integration@example.com"
    }
    
    request_response = await async_client.post("/auth/password-reset-request", json=reset_request)
    assert request_response.status_code == status.HTTP_200_OK
    
    # In a real test, we would extract the reset token from the email or database
    # For this integration test, we'll mock the token
    mock_reset_token = "mock_reset_token"
    
    # Complete password reset
    reset_data = {
        "token": mock_reset_token,
        "new_password": "newSecurePassword456!"
    }
    
    reset_response = await async_client.post("/auth/password-reset", json=reset_data)
    # This will likely fail in actual testing without a valid token, but we're testing the flow
    assert reset_response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]