#!/usr/bin/env python3
"""
Simple Phase 3 Test - Core functionality without FastAPI dependencies

Tests the core components: indexer and reviewer
"""

import sys
import os
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from processing import indexer
from ai import reviewer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_indexer_never_empty():
    """Test that indexer never returns empty chunks."""
    logger.info("=== Testing Indexer Fallback ===")
    
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
    
    logger.info("✅ Indexer tests PASSED - never returns empty chunks")
    return True


def test_reviewer_structure():
    """Test that reviewer returns proper structure."""
    logger.info("=== Testing Reviewer Structure ===")
    
    # Create test data
    test_chunks = [
        {
            "content": "def hello_world():\n    print('Hello, World!')",
            "file_path": "test.py",
            "language": "python",
            "start_line": 1,
            "end_line": 2
        }
    ]
    
    test_data = {
        "chunks": test_chunks,
        "files": [{"path": "test.py", "size": 50, "language": "python"}],
        "repo": "test/repo"
    }
    
    # Test reviewer engine creation
    review_engine = reviewer.ReviewEngine()
    assert review_engine is not None, "Should create review engine"
    logger.info("✓ Review engine created")
    
    # Test chunk selection
    important_chunks = review_engine._select_important_chunks(test_data)
    assert len(important_chunks) > 0, "Should select important chunks"
    logger.info(f"✓ Selected {len(important_chunks)} important chunks")
    
    # Test fallback analysis
    fallback = review_engine._create_fallback_analysis(test_data, test_chunks)
    assert isinstance(fallback, dict), "Fallback should return dict"
    assert "score" in fallback, "Fallback should have score"
    assert "issues" in fallback, "Fallback should have issues"
    assert "security" in fallback, "Fallback should have security"
    assert "architecture" in fallback, "Fallback should have architecture"
    assert "skills" in fallback, "Fallback should have skills"
    logger.info("✓ Fallback analysis structure is correct")
    
    logger.info("✅ Reviewer tests PASSED - proper structure guaranteed")
    return True


def test_heuristic_analysis():
    """Test heuristic analysis when AI fails."""
    logger.info("=== Testing Heuristic Analysis ===")
    
    test_chunks = [
        {
            "content": "def hello_world():\n    print('Hello, World!')\n# TODO: Add error handling",
            "file_path": "test.py",
            "start_line": 1
        }
    ]
    
    review_engine = reviewer.ReviewEngine()
    
    # Test each review type
    for review_type in ["quality", "security", "architecture", "skills"]:
        result = review_engine._heuristic_analysis(test_chunks, review_type)
        
        assert isinstance(result, dict), f"Heuristic {review_type} should return dict"
        assert "score" in result, f"Heuristic {review_type} should have score"
        assert isinstance(result["score"], (int, float)), f"Score should be number for {review_type}"
        assert 0 <= result["score"] <= 100, f"Score should be in range for {review_type}"
        
        logger.info(f"✓ Heuristic {review_type}: score {result['score']}")
    
    logger.info("✅ Heuristic analysis tests PASSED")
    return True


def test_complete_flow():
    """Test complete flow without FastAPI."""
    logger.info("=== Testing Complete Flow ===")
    
    # Step 1: Create test repository
    test_files = [
        {"path": "main.py", "size": 200, "language": "python", "download_url": ""},
        {"path": "utils.js", "size": 150, "language": "javascript", "download_url": ""}
    ]
    
    # Step 2: Process (Phase 2)
    logger.info("Step 2: Processing repository")
    process_result = indexer.create_repository_index({"files": test_files, "repo": "test/complete"})
    
    assert process_result["total_chunks"] > 0, "Processing should create chunks"
    assert len(process_result["chunks"]) > 0, "Should have chunk data"
    logger.info(f"✓ Processing complete: {process_result['total_chunks']} chunks created")
    
    # Step 3: Prepare review data
    review_data = {
        "chunks": process_result["chunks"],
        "files": test_files,
        "repo": "test/complete"
    }
    
    # Step 4: Test review preparation
    logger.info("Step 4: Testing review preparation")
    review_engine = reviewer.ReviewEngine()
    important_chunks = review_engine._select_important_chunks(review_data)
    
    assert len(important_chunks) > 0, "Should select chunks for review"
    logger.info(f"✓ Selected {len(important_chunks)} chunks for review")
    
    # Step 5: Test fallback analysis (simulating AI failure)
    logger.info("Step 5: Testing fallback analysis")
    fallback_result = review_engine._create_fallback_analysis(review_data, important_chunks)
    
    assert isinstance(fallback_result, dict), "Fallback should return dict"
    assert "score" in fallback_result, "Should have score"
    assert isinstance(fallback_result["score"], (int, float)), "Score should be number"
    assert 0 <= fallback_result["score"] <= 100, "Score should be in valid range"
    
    total_items = (
        len(fallback_result.get("issues", [])) +
        len(fallback_result.get("security", [])) +
        len(fallback_result.get("architecture", [])) +
        len(fallback_result.get("skills", []))
    )
    assert total_items > 0, "Should have some analysis results"
    
    logger.info(f"✓ Fallback analysis complete: score {fallback_result['score']}, {total_items} items")
    
    logger.info("✅ Complete flow test PASSED")
    return True


def main():
    """Run all Phase 3 core tests."""
    logger.info("=== Phase 3 Core Functionality Tests ===")
    
    tests = [
        ("Indexer Never Empty", test_indexer_never_empty),
        ("Reviewer Structure", test_reviewer_structure),
        ("Heuristic Analysis", test_heuristic_analysis),
        ("Complete Flow", test_complete_flow),
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
        logger.info("\n🎉 All Phase 3 core tests PASSED!")
        logger.info("✅ Phase 3 AI Review core functionality is working!")
        logger.info("✅ Chunk generation guarantee verified")
        logger.info("✅ Response structure guarantee verified")
        logger.info("✅ Fallback analysis verified")
        return True
    else:
        logger.error(f"\n❌ {failed} tests failed. Phase 3 needs fixes.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
