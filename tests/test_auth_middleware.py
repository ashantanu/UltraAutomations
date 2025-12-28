import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.middleware.auth import AuthMiddleware

# Create a mock Supabase client
mock_supabase = MagicMock()

# Create a test app
app = FastAPI()

# Add the middleware
with patch('app.middleware.auth.supabase', mock_supabase):
    app.add_middleware(AuthMiddleware)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/protected-route")
async def protected_route(request: Request):
    return {
        "message": "This is a protected route",
        "user": request.state.user.user.email if request.state.user.user else None
    }

# Create a test client
client = TestClient(app)

def test_health_endpoint():
    """Test that the health endpoint is accessible without authentication"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_protected_route_without_auth():
    """Test that protected routes require authentication"""
    response = client.get("/protected-route")
    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["detail"]

@patch('app.middleware.auth.supabase')
def test_protected_route_with_invalid_token(mock_supabase):
    """Test that protected routes reject invalid tokens"""
    # Configure mock to raise an exception for invalid token
    mock_supabase.auth.get_user.side_effect = Exception("Invalid token")
    
    response = client.get(
        "/protected-route",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

@patch('app.middleware.auth.supabase')
def test_protected_route_with_valid_token(mock_supabase):
    """Test that protected routes accept valid tokens"""
    # Configure mock to return a valid user
    mock_user = MagicMock()
    mock_user.user.email = "test@example.com"
    mock_supabase.auth.get_user.return_value = mock_user
    
    response = client.get(
        "/protected-route",
        headers={"Authorization": "Bearer valid_token"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "This is a protected route"
    assert response.json()["user"] == "test@example.com"

def test_auth_endpoints_accessible():
    """Test that auth endpoints are accessible without authentication"""
    # Test login endpoint
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "testpassword"}
    )
    # In this unit-test app, auth routes aren't mounted; the key point is the middleware
    # does NOT return 401 due to missing Authorization header.
    assert response.status_code == 404

    # Test register endpoint
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 404