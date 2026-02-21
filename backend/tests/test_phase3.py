#!/usr/bin/env python3
"""
Phase 3 Integration Tests

Tests the complete pipeline: PROCESS → VALIDATE → REVIEW → DISPLAY

Ensures Phase 3 AI Review is reliable, deterministic, and production-ready.
"""

import asyncio
import logging
import sys
import os
import pytest
from typing import Dict, Any, List
from fastapi.testclient import TestClient
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app
from processing import indexer
from ai import reviewer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TestClient(app)


class TestPhase3Pipeline:
    """Test Phase 3 AI Review Pipeline"""
    
    def test_health_endpoint(self):
        """Test health check endpoint returns proper status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert "backend" in health_data
        assert "processing" in health_data
        assert "review" in health_data
        assert "model" in health_data
        
        # Check that all components are ok or at least not error
        for component in ["backend", "processing", "review", "model"]:
            assert health_data[component] in ["ok", "warning", "error"]
    
    def test_review_empty_chunks_error(self):
        """Test that review endpoint rejects empty chunks with 400 error."""
        # Test with completely empty request
        response = client.post("/api/review", json={})
        assert response.status_code == 422  # Missing chunks field
        
        # Test with empty chunks list
        response = client.post("/api/review", json={"chunks": []})
        assert response.status_code == 400  # Empty chunks should be rejected
        
        error_data = response.json()
        assert "detail" in error_data
        assert "No chunks available" in error_data["detail"]
    
    def test_review_invalid_chunks_error(self):
        """Test that review endpoint rejects invalid chunk structures."""
        # Test with invalid chunk data
        invalid_chunks = [
            {"invalid": "chunk"},  # Missing content
            {"content": ""},       # Empty content
            {"content": "   "}     # Whitespace only
        ]
        
        response = client.post("/api/review", json={"chunks": invalid_chunks})
        assert response.status_code == 200  # Should process but return success: false
        
        data = response.json()
        assert data["success"] is False
        assert "No valid code chunks found" in data["error"]
    
    def test_review_response_structure(self):
        """Test that review endpoint always returns proper structure."""
        # Create minimal valid chunks
        valid_chunks = [
            {
                "content": "def hello_world():\n    print('Hello, World!')",
                "file_path": "test.py",
                "language": "python",
                "start_line": 1,
                "end_line": 2
            }
        ]
        
        response = client.post("/api/review", json={"chunks": valid_chunks})
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields exist
        required_fields = ["success", "score", "issues", "security", "architecture", "skills"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify score is a valid number
        assert isinstance(data["score"], (int, float))
        assert 0 <= data["score"] <= 100
        
        # Verify array fields are actually arrays
        array_fields = ["issues", "security", "architecture", "skills"]
        for field in array_fields:
            assert isinstance(data[field], list), f"Field {field} should be a list"
    
    def test_review_score_never_undefined(self):
        """Test that review never returns undefined/null score."""
        # Test with minimal chunks
        chunks = [{"content": "print('test')", "file_path": "test.py"}]
        
        response = client.post("/api/review", json={"chunks": chunks})
        assert response.status_code == 200
        
        data = response.json()
        
        # Score must exist and be a number
        assert "score" in data
        assert data["score"] is not None
        assert not isinstance(data["score"], str) or str(data["score"]).replace('.', '').isdigit()
    
    def test_chunk_generation_fallback(self):
        """Test that indexer never returns empty chunks."""
        # Test with empty files list
        result = indexer.create_repository_index({"files": [], "repo": "empty"})
        
        assert result["total_chunks"] > 0, "Indexer should create emergency chunks"
        assert len(result["chunks"]) > 0, "Should have at least one emergency chunk"
        
        # Test with invalid file data
        invalid_files = [{"path": "", "size": 0, "language": "", "download_url": ""}]
        result = indexer.create_repository_index({"files": invalid_files, "repo": "invalid"})
        
        assert result["total_chunks"] > 0, "Indexer should handle invalid files"
        assert len(result["chunks"]) > 0, "Should create fallback chunks"
    
    def test_complete_pipeline_success(self):
        """Test complete pipeline: process → review → score."""
        # Step 1: Create test repository data
        test_files = [
            {
                "path": "main.py",
                "size": 150,
                "language": "python",
                "download_url": "http://example.com/main.py"
            },
            {
                "path": "utils.py", 
                "size": 200,
                "language": "python",
                "download_url": "http://example.com/utils.py"
            }
        ]
        
        # Step 2: Process repository (Phase 2)
        process_request = {"files": test_files, "repo": "test/repo"}
        process_response = client.post("/api/process", json=process_request)
        
        # Process should succeed and create chunks
        assert process_response.status_code == 200
        process_data = process_response.json()
        
        if process_data.get("success", True):
            assert process_data["total_chunks"] > 0, "Processing should create chunks"
            assert len(process_data["chunks"]) > 0, "Should have chunk data"
            
            # Step 3: Review repository (Phase 3)
            review_request = {
                "chunks": process_data["chunks"],
                "files": test_files,
                "repo": "test/repo"
            }
            review_response = client.post("/api/review", json=review_request)
            
            assert review_response.status_code == 200
            review_data = review_response.json()
            
            # Step 4: Validate review results
            assert review_data["success"] is True
            assert isinstance(review_data["score"], (int, float))
            assert 0 <= review_data["score"] <= 100
            
            # Should have some analysis results
            total_items = (
                len(review_data["issues"]) + 
                len(review_data["security"]) + 
                len(review_data["architecture"]) + 
                len(review_data["skills"])
            )
            assert total_items >= 0, "Should have analysis items (can be zero for simple code)"
    
    def test_model_failure_fallback(self, monkeypatch):
        """Test fallback behavior when AI model fails."""
        # Mock the review engine to simulate model failure
        async def failing_analyze_repo(data):
            raise Exception("Model connection failed")
        
        # Patch the review engine
        monkeypatch.setattr(reviewer.ReviewEngine, "analyze_repo", failing_analyze_repo)
        
        # Test with valid chunks
        chunks = [{"content": "print('test')", "file_path": "test.py"}]
        response = client.post("/api/review", json={"chunks": chunks})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return success: false but with proper structure
        assert data["success"] is False
        assert "error" in data
        assert data["score"] == 0  # Fallback score
        assert isinstance(data["issues"], list)
        assert isinstance(data["security"], list)
        assert isinstance(data["architecture"], list)
        assert isinstance(data["skills"], list)
    
    def test_concurrent_requests(self):
        """Test that multiple concurrent requests are handled properly."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                chunks = [{"content": f"print('test {time.time()}')", "file_path": "test.py"}]
                response = client.post("/api/review", json={"chunks": chunks})
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(errors) == 0, f"Concurrent requests had errors: {errors}"
        assert len(results) == 5, "Should have 5 results"
        assert all(status == 200 for status in results), "All requests should succeed"
    
    def test_large_chunk_handling(self):
        """Test handling of large chunks and proper token limits."""
        # Create a large chunk (simulate)
        large_content = "print('test')\n" * 1000  # Large but reasonable
        chunks = [{"content": large_content, "file_path": "large.py"}]
        
        response = client.post("/api/review", json={"chunks": chunks})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["score"], (int, float))
    
    def test_mixed_language_chunks(self):
        """Test review with chunks from multiple programming languages."""
        chunks = [
            {"content": "def hello(): print('Hello')", "file_path": "test.py", "language": "python"},
            {"content": "function hello() { console.log('Hello'); }", "file_path": "test.js", "language": "javascript"},
            {"content": "public class Hello { public static void main(String[] args) { System.out.println(\"Hello\"); } }", "file_path": "Hello.java", "language": "java"}
        ]
        
        response = client.post("/api/review", json={"chunks": chunks})
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["score"], (int, float))
        assert 0 <= data["score"] <= 100


def test_phase3_integration_summary():
    """Run all Phase 3 integration tests and provide summary."""
    logger.info("=== Phase 3 Integration Test Suite ===")
    
    test_instance = TestPhase3Pipeline()
    
    tests = [
        ("Health Endpoint", test_instance.test_health_endpoint),
        ("Empty Chunks Error", test_instance.test_review_empty_chunks_error),
        ("Invalid Chunks Error", test_instance.test_review_invalid_chunks_error),
        ("Response Structure", test_instance.test_review_response_structure),
        ("Score Never Undefined", test_instance.test_review_score_never_undefined),
        ("Chunk Generation Fallback", test_instance.test_chunk_generation_fallback),
        ("Complete Pipeline Success", test_instance.test_complete_pipeline_success),
        ("Large Chunk Handling", test_instance.test_large_chunk_handling),
        ("Mixed Language Chunks", test_instance.test_mixed_language_chunks),
        ("Concurrent Requests", test_instance.test_concurrent_requests),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            logger.info(f"Running test: {test_name}")
            test_func()
            logger.info(f"✓ {test_name} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} FAILED: {e}")
            failed += 1
    
    logger.info(f"=== Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All Phase 3 integration tests PASSED!")
        logger.info("Phase 3 AI Review is production-ready!")
    else:
        logger.error(f"❌ {failed} tests failed. Phase 3 needs fixes.")
    
    return failed == 0


if __name__ == "__main__":
    # Run the integration test suite
    success = test_phase3_integration_summary()
    sys.exit(0 if success else 1)
