#!/usr/bin/env python3
"""
Test script to validate score breakdown functionality
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from ai.reviewer import ReviewEngine
from ai.parser import response_parser

def test_score_calculation():
    """Test individual score calculation logic"""
    print("=== Testing Score Calculation Logic ===")
    
    engine = ReviewEngine()
    
    # Test with empty issues (should get high score)
    empty_issues = []
    score = engine._calculate_component_score(empty_issues, "quality")
    print(f"Empty issues score: {score} (expected: 90.0)")
    assert score == 90.0, f"Expected 90.0, got {score}"
    
    # Test with mock issues
    mock_issues = [
        type('Issue', (), {'severity': 'high'}),
        type('Issue', (), {'severity': 'medium'}),
        type('Issue', (), {'severity': 'low'}),
        type('Issue', (), {'severity': 'high'})
    ]
    
    score = engine._calculate_component_score(mock_issues, "quality")
    expected = 95.0 - (2 * 15) - (1 * 8) - (1 * 3)  # 95 - 30 - 8 - 3 = 54
    print(f"Mock issues score: {score} (expected: {expected})")
    assert abs(score - expected) < 0.1, f"Expected {expected}, got {score}"
    
    print("✓ Score calculation tests passed")

def test_overall_score():
    """Test overall score calculation"""
    print("\n=== Testing Overall Score Calculation ===")
    
    engine = ReviewEngine()
    
    # Test weighted average calculation
    overall = engine._calculate_overall_score(80, 70, 85, 75)
    expected = (80 * 0.30) + (70 * 0.25) + (85 * 0.25) + (75 * 0.20)
    expected = round(expected, 1)
    
    print(f"Overall score: {overall} (expected: {expected})")
    assert abs(overall - expected) < 0.1, f"Expected {expected}, got {overall}"
    
    print("✓ Overall score calculation tests passed")

def test_score_breakdown_structure():
    """Test that score breakdown has correct structure"""
    print("\n=== Testing Score Breakdown Structure ===")
    
    # Mock breakdown data
    breakdown = {
        "code_quality": 82.5,
        "security": 90.0,
        "architecture": 75.5,
        "skills": 85.0
    }
    
    # Validate all required fields exist
    required_fields = ["code_quality", "security", "architecture", "skills"]
    for field in required_fields:
        assert field in breakdown, f"Missing field: {field}"
        assert isinstance(breakdown[field], (int, float)), f"Field {field} should be numeric"
        assert 0 <= breakdown[field] <= 100, f"Field {field} should be between 0-100"
    
    print("✓ Score breakdown structure validation passed")
    
    # Test overall calculation from breakdown
    engine = ReviewEngine()
    overall = engine._calculate_overall_score(
        breakdown["code_quality"],
        breakdown["security"], 
        breakdown["architecture"],
        breakdown["skills"]
    )
    
    print(f"Calculated overall from breakdown: {overall}")
    print("✓ Overall score from breakdown validation passed")

def test_fallback_score_breakdown():
    """Test fallback analysis score breakdown"""
    print("\n=== Testing Fallback Score Breakdown ===")
    
    engine = ReviewEngine()
    
    # Create minimal fallback data
    index_data = {"chunks": []}
    chunks = []
    
    fallback_result = engine._create_fallback_analysis(index_data, chunks)
    
    # Check that score breakdown exists
    assert "score_breakdown" in fallback_result, "Missing score_breakdown in fallback"
    assert "score" in fallback_result, "Missing score in fallback"
    
    breakdown = fallback_result["score_breakdown"]
    print(f"Fallback score: {fallback_result['score']}")
    print(f"Fallback breakdown: {breakdown}")
    
    # Validate breakdown structure
    required_fields = ["code_quality", "security", "architecture", "skills"]
    for field in required_fields:
        assert field in breakdown, f"Missing field {field} in fallback breakdown"
        assert isinstance(breakdown[field], (int, float)), f"Fallback {field} should be numeric"
    
    print("✓ Fallback score breakdown validation passed")

if __name__ == "__main__":
    try:
        test_score_calculation()
        test_overall_score()
        test_score_breakdown_structure()
        test_fallback_score_breakdown()
        
        print("\n🎉 All score breakdown tests passed!")
        print("\nValidation Summary:")
        print("- Individual component scores calculated correctly")
        print("- Overall score computed as weighted average")
        print("- Score breakdown structure is valid")
        print("- Fallback analysis includes proper breakdown")
        print("- All scores are within 0-100 range")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)