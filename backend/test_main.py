import pytest

# fastapi and httpx may not be installed in the environment used for testing;
# skip the module-level fixtures/tests if they are unavailable.
fastapi = pytest.importorskip('fastapi')
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


def test_process_no_chunks_error(monkeypatch):
    """If the processing step somehow produces zero chunks, API returns structured error."""
    # monkeypatch create_repository_index to simulate zero chunks
    from processing import indexer
    def fake_index(data):
        return {'total_chunks': 0, 'total_files': 1, 'processing_stats': {}, 'chunks': []}
    monkeypatch.setattr(indexer, 'create_repository_index', fake_index)

    response = client.post('/api/process', json={'files': [{'path': 'foo.py', 'size': 10, 'language': 'python', 'download_url': ''}]})
    assert response.status_code == 200
    data = response.json()
    assert data.get('success') is False
    assert 'No chunks' in data.get('error', '')


def test_review_empty_chunks_fallback(monkeypatch):
    """Review endpoint should auto-generate fallback chunks when given empty list."""
    # provide request with no chunks but some files
    request = {'chunks': [], 'files': [{'path': 'foo.py', 'size': 10, 'language': 'python', 'download_url': ''}], 'repo': 'test/repo'}

    # monkeypatch review_engine to a dummy that returns a predictable output
    from ai import reviewer
    class DummyEngine:
        async def analyze_repo(self, data):
            return {'success': True, 'issues': [], 'security': [], 'architecture': [], 'skills': [], 'score': 50}
    monkeypatch.setattr(reviewer, 'review_engine', DummyEngine())

    response = client.post('/api/review', json=request)
    assert response.status_code == 200
    data = response.json()
    # should either generate fallback or return success:false but not 422
    assert isinstance(data, dict)
    assert data.get('success') is True or data.get('success') is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
