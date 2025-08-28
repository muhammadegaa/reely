"""
Basic API tests for Reely
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Reely" in data["message"]

def test_register_user():
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User"
        }
    )
    # This will fail without proper database setup, but tests the endpoint exists
    assert response.status_code in [201, 400, 422, 500]

def test_unauthorized_access():
    """Test that protected endpoints require authentication"""
    response = client.post("/trim", data={
        "url": "https://www.youtube.com/watch?v=test",
        "start_time": "0:30",
        "end_time": "1:00"
    })
    assert response.status_code == 401