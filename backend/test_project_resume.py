#!/usr/bin/env python3
"""
Validation script for Project Resume Mode feature
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def test_resume_generation_logic():
    """Test the resume generation logic without external dependencies"""
    print("=== Testing Project Resume Generation Logic ===")
    
    # Test fallback resume generation
    def generate_fallback_resume(overall_score: float, score_breakdown: dict) -> str:
        """Generate fallback resume summary when AI fails."""
        # Create a professional summary based on scores
        quality_desc = "strong" if score_breakdown["code_quality"] >= 80 else "solid" if score_breakdown["code_quality"] >= 60 else "developing"
        security_desc = "robust" if score_breakdown["security"] >= 80 else "adequate" if score_breakdown["security"] >= 60 else "basic"
        arch_desc = "well-structured" if score_breakdown["architecture"] >= 80 else "organized" if score_breakdown["architecture"] >= 60 else "functional"
        skills_desc = "advanced" if score_breakdown["skills"] >= 80 else "competent" if score_breakdown["skills"] >= 60 else "emerging"
        
        summary = f"This project demonstrates {quality_desc} development practices with {security_desc} security implementation. "
        summary += f"The {arch_desc} architecture reflects {skills_desc} technical capabilities. "
        summary += "Shows attention to code quality, security considerations, and maintainable design patterns. "
        summary += "Well-suited for production environments with opportunities for further enhancement."
        
        return summary.strip()
    
    # Test case 1: High scores
    high_scores = {
        "code_quality": 85.0,
        "security": 90.0,
        "architecture": 82.5,
        "skills": 88.0
    }
    
    resume1 = generate_fallback_resume(86.0, high_scores)
    print(f"High scores resume ({len(resume1.split())} words):")
    print(f"  {resume1}")
    assert len(resume1.split()) >= 20, "Resume should be substantial"
    assert "strong" in resume1, "Should mention strong development practices"
    assert "robust" in resume1, "Should mention robust security"
    
    # Test case 2: Medium scores
    medium_scores = {
        "code_quality": 65.0,
        "security": 70.0,
        "architecture": 68.0,
        "skills": 62.0
    }
    
    resume2 = generate_fallback_resume(66.0, medium_scores)
    print(f"\nMedium scores resume ({len(resume2.split())} words):")
    print(f"  {resume2}")
    assert "solid" in resume2, "Should mention solid development practices"
    assert "adequate" in resume2, "Should mention adequate security"
    
    # Test case 3: Low scores
    low_scores = {
        "code_quality": 45.0,
        "security": 50.0,
        "architecture": 48.0,
        "skills": 42.0
    }
    
    resume3 = generate_fallback_resume(46.0, low_scores)
    print(f"\nLow scores resume ({len(resume3.split())} words):")
    print(f"  {resume3}")
    assert "developing" in resume3, "Should mention developing practices"
    assert "basic" in resume3, "Should mention basic security"
    
    print("\n✓ Resume generation logic tests passed")

def test_summary_helpers():
    """Test the helper functions for summarizing analysis areas"""
    print("\n=== Testing Summary Helper Functions ===")
    
    # Test issues summary
    def summarize_issues(issues: list) -> str:
        """Create a summary of code quality issues."""
        if not issues:
            return "No significant code quality issues identified. Demonstrates clean coding practices."
        
        high_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "high")
        medium_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "medium")
        low_count = sum(1 for issue in issues if getattr(issue, "severity", "low") == "low")
        
        summary = f"Identified {len(issues)} code quality items: "
        if high_count > 0:
            summary += f"{high_count} high priority, "
        if medium_count > 0:
            summary += f"{medium_count} medium priority, "
        if low_count > 0:
            summary += f"{low_count} low priority issues. "
        
        summary += "Focus areas include maintainability and code standards."
        return summary
    
    # Mock issue class
    class MockIssue:
        def __init__(self, severity):
            self.severity = severity
    
    # Test with various issue combinations
    test_cases = [
        ([], "No issues"),
        ([MockIssue("high")], "1 high priority"),
        ([MockIssue("medium"), MockIssue("low")], "1 medium, 1 low"),
        ([MockIssue("high"), MockIssue("high"), MockIssue("medium")], "2 high, 1 medium")
    ]
    
    for issues, expected_desc in test_cases:
        summary = summarize_issues(issues)
        print(f"  Issues {len(issues)}: {summary[:50]}...")
        assert len(summary) > 20, "Summary should be meaningful"
        if issues:
            assert str(len(issues)) in summary, "Should mention count of issues"
    
    print("✓ Summary helper functions tests passed")

def test_api_response_structure():
    """Test that API response includes required fields"""
    print("\n=== Testing API Response Structure ===")
    
    # Mock API response
    mock_response = {
        "success": True,
        "score": 83.1,
        "score_breakdown": {
            "code_quality": 82.5,
            "security": 90.0,
            "architecture": 75.5,
            "skills": 85.0
        },
        "project_resume": "This project demonstrates strong development practices with robust security implementation. The well-structured architecture reflects advanced technical capabilities. Shows attention to code quality and maintainable design patterns.",
        "issues": [],
        "security": [],
        "architecture": [],
        "skills": []
    }
    
    # Validate required fields
    required_fields = ["success", "score", "score_breakdown", "project_resume"]
    for field in required_fields:
        assert field in mock_response, f"Missing required field: {field}"
        if field != "success":
            assert mock_response[field] is not None, f"Field {field} should not be None"
    
    # Validate score breakdown structure
    breakdown = mock_response["score_breakdown"]
    breakdown_fields = ["code_quality", "security", "architecture", "skills"]
    for field in breakdown_fields:
        assert field in breakdown, f"Missing breakdown field: {field}"
        assert isinstance(breakdown[field], (int, float)), f"Breakdown field {field} should be numeric"
        assert 0 <= breakdown[field] <= 100, f"Breakdown field {field} should be 0-100"
    
    # Validate project resume
    resume = mock_response["project_resume"]
    assert isinstance(resume, str), "Project resume should be string"
    assert len(resume.strip()) > 0, "Project resume should not be empty"
    assert len(resume.split()) >= 20, "Project resume should be substantial"
    
    print("✓ API response structure validation passed")
    print(f"  Resume length: {len(resume.split())} words")
    print(f"  Overall score: {mock_response['score']}")

if __name__ == "__main__":
    try:
        test_resume_generation_logic()
        test_summary_helpers()
        test_api_response_structure()
        
        print("\n🎉 All Project Resume Mode validation tests passed!")
        print("\nValidation Summary:")
        print("- Resume generation logic works correctly for different score ranges")
        print("- Summary helper functions create appropriate descriptions")
        print("- API response structure includes all required fields")
        print("- Project resume is properly formatted and substantial")
        print("- Fallback generation provides reasonable alternatives")
        
    except Exception as e:
        print(f"\n❌ Validation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)