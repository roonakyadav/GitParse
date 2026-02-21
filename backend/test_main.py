import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "RepoMind AI API is running"
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_analyze_invalid_url():
    """Test analyze endpoint with invalid URL."""
    response = client.post(
        "/api/analyze",
        json={"repo_url": "invalid-url"}
    )
    assert response.status_code == 400
    assert "Invalid repository URL" in response.json()["detail"]


def test_analyze_empty_url():
    """Test analyze endpoint with empty URL."""
    response = client.post(
        "/api/analyze",
        json={"repo_url": ""}
    )
    assert response.status_code == 400


def test_analyze_nonexistent_repo():
    """Test analyze endpoint with non-existent repository."""
    response = client.post(
        "/api/analyze",
        json={"repo_url": "https://github.com/nonexistent/nonexistent"}
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_analyze_missing_repo_url():
    """Test analyze endpoint with missing repo_url field."""
    response = client.post(
        "/api/analyze",
        json={}
    )
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
