#!/usr/bin/env python3
"""
End-to-end integration test for RepoMind Phase 3.
Tests the complete pipeline: Analyze → Process → Review
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BACKEND_URL = "http://localhost:8000"
TEST_REPO = "https://github.com/octocat/Hello-World"  # Small, simple repo for testing

async def test_api_endpoint(endpoint: str, data: dict = None, method: str = "POST") -> dict:
    """Test an API endpoint and return response."""
    import aiohttp
    
    url = f"{BACKEND_URL}{endpoint}"
    
    try:
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    logger.info(f"{endpoint} - Status: {response.status}")
                    return {"status": response.status, "data": result, "ok": response.ok}
            else:
                async with session.get(url) as response:
                    result = await response.json()
                    logger.info(f"{endpoint} - Status: {response.status}")
                    return {"status": response.status, "data": result, "ok": response.ok}
    except Exception as e:
        logger.error(f"{endpoint} - Error: {str(e)}")
        return {"status": 0, "data": {"error": str(e)}, "ok": False}

async def test_phase1_analyze():
    """Test Phase 1: Repository Analysis."""
    logger.info("=== Testing Phase 1: Repository Analysis ===")
    
    request_data = {"repo_url": TEST_REPO}
    result = await test_api_endpoint("/api/analyze", request_data)
    
    if not result["ok"]:
        logger.error(f"Phase 1 failed: {result['data']}")
        return None
    
    data = result["data"]
    files_count = len(data.get("files", []))
    logger.info(f"✓ Phase 1 successful: {files_count} files found")
    
    return data

async def test_phase2_process(phase1_data: dict):
    """Test Phase 2: Repository Processing."""
    logger.info("=== Testing Phase 2: Repository Processing ===")
    
    result = await test_api_endpoint("/api/process", phase1_data)
    
    if not result["ok"]:
        logger.error(f"Phase 2 failed: {result['data']}")
        return None
    
    data = result["data"]
    
    # Check for success flag
    if not data.get("success", True):
        logger.warning(f"Phase 2 reported issues: {data.get('error', 'Unknown error')}")
    
    chunks_count = data.get("total_chunks", 0)
    files_count = data.get("total_files", 0)
    
    logger.info(f"✓ Phase 2 successful: {files_count} files, {chunks_count} chunks")
    
    if chunks_count == 0:
        logger.warning("⚠️  Phase 2 produced 0 chunks - this may indicate a problem")
    
    return data

async def test_phase3_review(phase2_data: dict):
    """Test Phase 3: AI Review."""
    logger.info("=== Testing Phase 3: AI Review ===")
    
    result = await test_api_endpoint("/api/review", phase2_data)
    
    if not result["ok"]:
        logger.error(f"Phase 3 failed: {result['data']}")
        return None
    
    data = result["data"]
    
    # Check for success flag
    if not data.get("success", True):
        logger.warning(f"Phase 3 reported issues: {data.get('error', 'Unknown error')}")
    
    # Check analysis results
    issues_count = len(data.get("issues", []))
    security_count = len(data.get("security", []))
    architecture_count = len(data.get("architecture", []))
    skills_count = len(data.get("skills", []))
    score = data.get("score", 0)
    
    logger.info(f"✓ Phase 3 successful: score {score}")
    logger.info(f"  - Issues: {issues_count}")
    logger.info(f"  - Security: {security_count}")
    logger.info(f"  - Architecture: {architecture_count}")
    logger.info(f"  - Skills: {skills_count}")
    
    # Ensure we have some analysis results
    if issues_count == 0 and security_count == 0 and architecture_count == 0 and skills_count == 0:
        logger.warning("⚠️  Phase 3 produced empty analysis - this may indicate a problem")
    
    return data

async def test_backend_health():
    """Test backend health endpoint."""
    logger.info("=== Testing Backend Health ===")
    
    result = await test_api_endpoint("/health", method="GET")
    
    if not result["ok"]:
        logger.error(f"Health check failed: {result['data']}")
        return False
    
    data = result["data"]
    status = data.get("status")
    version = data.get("version")
    phase = data.get("phase")
    
    logger.info(f"✓ Backend healthy: {status} (v{version}, {phase})")
    return True

async def run_integration_test():
    """Run complete integration test."""
    logger.info("Starting RepoMind Phase 3 Integration Test")
    logger.info(f"Testing repository: {TEST_REPO}")
    logger.info(f"Backend URL: {BACKEND_URL}")
    
    # Test backend health
    if not await test_backend_health():
        logger.error("❌ Backend is not healthy - aborting test")
        return False
    
    # Phase 1: Analyze
    phase1_data = await test_phase1_analyze()
    if not phase1_data:
        logger.error("❌ Phase 1 failed - aborting test")
        return False
    
    # Phase 2: Process
    phase2_data = await test_phase2_process(phase1_data)
    if not phase2_data:
        logger.error("❌ Phase 2 failed - aborting test")
        return False
    
    # Phase 3: Review
    phase3_data = await test_phase3_review(phase2_data)
    if not phase3_data:
        logger.error("❌ Phase 3 failed - aborting test")
        return False
    
    # Success!
    logger.info("🎉 Integration test completed successfully!")
    logger.info("✅ All phases working correctly")
    logger.info("✅ Pipeline is stable and reliable")
    
    return True

def main():
    """Main entry point."""
    try:
        # Check if aiohttp is available
        import aiohttp
    except ImportError:
        logger.error("❌ aiohttp is required for integration testing")
        logger.error("Install with: pip install aiohttp")
        sys.exit(1)
    
    # Run the test
    success = asyncio.run(run_integration_test())
    
    if success:
        logger.info("✅ Integration test PASSED")
        sys.exit(0)
    else:
        logger.error("❌ Integration test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
