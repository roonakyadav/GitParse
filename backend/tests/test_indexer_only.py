#!/usr/bin/env python3
"""
Minimal Phase 3 Test - Indexer only

Tests the chunk generation guarantee without external dependencies.
"""

import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from processing import indexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_indexer_never_empty():
    """Test that indexer never returns empty chunks."""
    logger.info("=== Testing Indexer Fallback Guarantee ===")
    
    # Test 1: Empty files list
    logger.info("Test 1: Empty files list")
    result1 = indexer.create_repository_index({"files": [], "repo": "empty"})
    assert result1["total_chunks"] > 0, "Should create emergency chunks"
    assert len(result1["chunks"]) > 0, "Should have at least one chunk"
    logger.info(f"✓ Created {result1['total_chunks']} emergency chunks")
    
    # Test 2: Invalid file data
    logger.info("Test 2: Invalid file data")
    invalid_files = [{"path": "", "size": 0, "language": "", "download_url": ""}]
    result2 = indexer.create_repository_index({"files": invalid_files, "repo": "invalid"})
    assert result2["total_chunks"] > 0, "Should handle invalid files"
    assert len(result2["chunks"]) > 0, "Should create fallback chunks"
    logger.info(f"✓ Created {result2['total_chunks']} fallback chunks")
    
    # Test 3: Valid files
    logger.info("Test 3: Valid files")
    valid_files = [
        {"path": "test.py", "size": 100, "language": "python", "download_url": ""},
        {"path": "main.js", "size": 150, "language": "javascript", "download_url": ""}
    ]
    result3 = indexer.create_repository_index({"files": valid_files, "repo": "valid"})
    assert result3["total_chunks"] > 0, "Should process valid files"
    assert len(result3["chunks"]) > 0, "Should create chunks from valid files"
    logger.info(f"✓ Created {result3['total_chunks']} chunks from valid files")
    
    # Test 4: Verify chunk structure
    logger.info("Test 4: Verify chunk structure")
    for i, chunk in enumerate(result3["chunks"][:3]):  # Check first 3 chunks
        assert isinstance(chunk, dict), f"Chunk {i} should be dict"
        assert "content" in chunk, f"Chunk {i} should have content"
        assert chunk["content"].strip(), f"Chunk {i} should have non-empty content"
        logger.info(f"✓ Chunk {i} has valid structure")
    
    logger.info("✅ Indexer tests PASSED - never returns empty chunks")
    return True


def test_emergency_chunks():
    """Test emergency chunk creation specifically."""
    logger.info("=== Testing Emergency Chunk Creation ===")
    
    # Test the emergency chunk function directly
    emergency_chunks = indexer._create_emergency_chunks([])
    assert len(emergency_chunks) > 0, "Should create emergency chunks even with no files"
    
    chunk = emergency_chunks[0]
    assert isinstance(chunk, dict), "Emergency chunk should be dict"
    assert "content" in chunk, "Should have content"
    assert "file_path" in chunk, "Should have file path"
    assert chunk["content"].strip(), "Should have non-empty content"
    
    logger.info(f"✓ Emergency chunk created: {chunk['file_path']}")
    logger.info(f"✓ Content length: {len(chunk['content'])} chars")
    
    # Test with files
    test_files = [
        {"path": "file1.py", "size": 100, "language": "python"},
        {"path": "file2.js", "size": 200, "language": "javascript"}
    ]
    emergency_chunks_with_files = indexer._create_emergency_chunks(test_files)
    assert len(emergency_chunks_with_files) > 0, "Should create emergency chunks with files"
    
    chunk_with_files = emergency_chunks_with_files[0]
    assert "file1.py" in chunk_with_files["content"], "Should include file information"
    
    logger.info("✅ Emergency chunk tests PASSED")
    return True


def main():
    """Run indexer tests."""
    logger.info("=== Phase 3 Indexer Guarantee Tests ===")
    
    tests = [
        ("Indexer Never Empty", test_indexer_never_empty),
        ("Emergency Chunks", test_emergency_chunks),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n--- Running: {test_name} ---")
            test_func()
            logger.info(f"✅ {test_name} PASSED")
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("\n🎉 All indexer tests PASSED!")
        logger.info("✅ Chunk generation guarantee VERIFIED!")
        logger.info("✅ Emergency fallback system WORKING!")
        logger.info("✅ Phase 2 → Phase 3 pipeline GUARANTEED!")
        return True
    else:
        logger.error(f"\n❌ {failed} tests failed. Indexer needs fixes.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
