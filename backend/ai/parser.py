import json
import logging
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

class Issue(BaseModel):
    type: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    message: str
    file: str
    line: int
    suggestion: str

class SecurityIssue(BaseModel):
    type: str = Field(default="security")
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    message: str
    file: str
    line: int
    cwe: Optional[str] = None
    suggestion: str

class ArchitectureIssue(BaseModel):
    type: str = Field(default="architecture")
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    message: str
    file: str
    line: int
    principle: Optional[str] = None
    suggestion: str

class SkillGap(BaseModel):
    category: str = Field(pattern="^(language|framework|pattern|tool)$")
    skill: str
    level: str = Field(pattern="^(beginner|intermediate|advanced)$")
    gap: str
    resource: Optional[str] = None
    priority: str = Field(pattern="^(low|medium|high)$")

class ReviewResult(BaseModel):
    issues: List[Issue] = Field(default_factory=list)
    security: List[SecurityIssue] = Field(default_factory=list)
    architecture: List[ArchitectureIssue] = Field(default_factory=list)
    skills: List[SkillGap] = Field(default_factory=list)
    score: int = Field(default=50, ge=0, le=100)

    @field_validator('score')
    @classmethod
    def calculate_score(cls, v, values):
        """Calculate overall score based on issues."""
        if v != 50:  # If explicitly set, use it
            return v
        
        # Auto-calculate based on issues
        total_issues = (
            len(values.get('issues', [])) +
            len(values.get('security', [])) +
            len(values.get('architecture', []))
        )
        
        # Base score starts at 100, subtract points for issues
        score = 100
        score -= min(total_issues * 5, 50)  # Max 50 points deduction
        
        # Extra deduction for critical issues
        critical_issues = sum(
            1 for issue_list in [values.get('issues', []), values.get('security', []), values.get('architecture', [])]
            for issue in issue_list
            if issue.severity == 'critical'
        )
        score -= min(critical_issues * 10, 30)  # Max 30 points deduction
        
        return max(0, min(100, score))

class ResponseParser:
    def __init__(self):
        self.cache = {}
    
    def extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract JSON from LLM response with multiple fallback strategies."""
        logger.debug(f"ai.parser: Parsing response of length {len(response)}")
        
        # If response is already a dict, return it
        if isinstance(response, dict):
            logger.debug("ai.parser: Response is already a dict")
            return response
            
        original_response = response
        
        # Strategy 1: Try direct JSON parsing first
        try:
            result = json.loads(response.strip())
            logger.debug("ai.parser: Direct JSON parsing succeeded")
            return result
        except json.JSONDecodeError:
            logger.debug("ai.parser: Direct JSON parsing failed")
            pass
        
        # Strategy 2: Extract JSON from markdown code blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'```JSON\s*(.*?)\s*```'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    result = json.loads(match.strip())
                    logger.debug(f"ai.parser: Extracted JSON from markdown with pattern {pattern}")
                    return result
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Find JSON objects in the text
        json_object_patterns = [
            r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # Nested objects
            r'\{[^{}]*\}',  # Simple objects
        ]
        
        for pattern in json_object_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    result = json.loads(match)
                    logger.debug(f"ai.parser: Found JSON object with pattern {pattern}")
                    return result
                except json.JSONDecodeError:
                    continue
        
        # Strategy 4: Try to fix common JSON issues
        try:
            # Remove common non-JSON prefixes/suffixes
            cleaned = response.strip()
            
            # Remove markdown indicators
            cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            
            # Remove explanatory text before/after JSON
            json_start = cleaned.find('{')
            json_end = cleaned.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_extract = cleaned[json_start:json_end + 1]
                result = json.loads(json_extract)
                logger.debug("ai.parser: Fixed JSON by extracting main object")
                return result
                
        except json.JSONDecodeError:
            logger.debug("ai.parser: JSON fixing failed")
            pass
        
        # Strategy 5: Last resort - try to construct minimal valid JSON
        try:
            # Look for key-value patterns
            if '"issues"' in response or '"security"' in response or '"architecture"' in response:
                logger.warning("ai.parser: Attempting partial JSON reconstruction")
                return self._reconstruct_partial_json(response)
        except Exception as e:
            logger.debug(f"ai.parser: Partial reconstruction failed: {str(e)}")
        
        logger.error(f"ai.parser: All JSON extraction strategies failed. Response preview: {original_response[:200]}...")
        return None
    
    def _reconstruct_partial_json(self, response: str) -> Dict:
        """Attempt to reconstruct partial JSON from malformed response."""
        result = {"issues": [], "security": [], "architecture": [], "skills": [], "score": 50}
        
        # Look for severity indicators
        severity_pattern = r'"severity":\s*"(low|medium|high|critical)"'
        severities = re.findall(severity_pattern, response)
        
        # Look for message patterns
        message_pattern = r'"message":\s*"([^"]+)"'
        messages = re.findall(message_pattern, response)
        
        # If we found some structured data, try to use it
        if severities and messages:
            logger.info("ai.parser: Reconstructed partial JSON from response")
            # Create a minimal issue based on found data
            if '"issues"' in response:
                result["issues"] = [{
                    "type": "quality",
                    "severity": severities[0],
                    "message": messages[0] if messages else "Code quality issue detected",
                    "file": "unknown",
                    "line": 1,
                    "suggestion": "Review and improve code quality"
                }]
            
            # Adjust score based on severities found
            if "critical" in severities:
                result["score"] = 30
            elif "high" in severities:
                result["score"] = 50
            elif "medium" in severities:
                result["score"] = 70
            else:
                result["score"] = 85
        
        return result
    
    def parse_review_response(self, response: str, review_type: str) -> Dict[str, Any]:
        """Parse and validate review response."""
        logger.info(f"ai.parser: Parsing {review_type} response of length {len(response)}")
        
        # Extract JSON from response
        json_data = self.extract_json_from_response(response)
        if not json_data:
            logger.error(f"ai.parser: Failed to parse {review_type} review response")
            return self._get_empty_result(review_type)
        
        logger.info(f"ai.parser: Extracted JSON for {review_type}: {json_data}")
        
        try:
            # Validate based on review type
            if review_type == "quality":
                return self._parse_quality_review(json_data)
            elif review_type == "security":
                return self._parse_security_review(json_data)
            elif review_type == "architecture":
                return self._parse_architecture_review(json_data)
            elif review_type == "skills":
                return self._parse_skills_review(json_data)
            else:
                logger.error(f"Unknown review type: {review_type}")
                return self._get_empty_result(review_type)
        
        except Exception as e:
            logger.error(f"Error parsing {review_type} review: {str(e)}")
            return self._get_empty_result(review_type)
    
    def _parse_quality_review(self, data: Dict) -> Dict[str, Any]:
        """Parse quality review response."""
        result = {"issues": [], "score": 50}
        
        if "issues" in data:
            for issue_data in data["issues"]:
                try:
                    issue = Issue(**issue_data)
                    result["issues"].append(issue.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid quality issue: {str(e)}")
        
        if "score" in data and isinstance(data["score"], (int, float)):
            result["score"] = max(0, min(100, int(data["score"])))
        
        return result
    
    def _parse_security_review(self, data: Dict) -> Dict[str, Any]:
        """Parse security review response."""
        result = {"security": [], "score": 50}
        
        if "security" in data:
            for issue_data in data["security"]:
                try:
                    issue = SecurityIssue(**issue_data)
                    result["security"].append(issue.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid security issue: {str(e)}")
        
        if "score" in data and isinstance(data["score"], (int, float)):
            result["score"] = max(0, min(100, int(data["score"])))
        
        return result
    
    def _parse_architecture_review(self, data: Dict) -> Dict[str, Any]:
        """Parse architecture review response."""
        result = {"architecture": [], "score": 50}
        
        if "architecture" in data:
            for issue_data in data["architecture"]:
                try:
                    issue = ArchitectureIssue(**issue_data)
                    result["architecture"].append(issue.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid architecture issue: {str(e)}")
        
        if "score" in data and isinstance(data["score"], (int, float)):
            result["score"] = max(0, min(100, int(data["score"])))
        
        return result
    
    def _parse_skills_review(self, data: Dict) -> Dict[str, Any]:
        """Parse skills review response."""
        result = {"skills": [], "score": 50}
        
        if "skills" in data:
            for skill_data in data["skills"]:
                try:
                    skill = SkillGap(**skill_data)
                    result["skills"].append(skill.model_dump())
                except Exception as e:
                    logger.warning(f"Invalid skill gap: {str(e)}")
        
        if "score" in data and isinstance(data["score"], (int, float)):
            result["score"] = max(0, min(100, int(data["score"])))
        
        return result
    
    def _get_empty_result(self, review_type: str) -> Dict[str, Any]:
        """Get empty result for failed parsing."""
        if review_type == "quality":
            return {"issues": [], "score": 50}
        elif review_type == "security":
            return {"security": [], "score": 50}
        elif review_type == "architecture":
            return {"architecture": [], "score": 50}
        elif review_type == "skills":
            return {"skills": [], "score": 50}
        else:
            return {"score": 50}
    
    def merge_results(self, results: List[Dict[str, Any]]) -> ReviewResult:
        """Merge multiple review results into final report."""
        merged = ReviewResult()
        
        for result in results:
            if "issues" in result:
                merged.issues.extend([Issue(**issue) for issue in result["issues"]])
            if "security" in result:
                merged.security.extend([SecurityIssue(**issue) for issue in result["security"]])
            if "architecture" in result:
                merged.architecture.extend([ArchitectureIssue(**issue) for issue in result["architecture"]])
            if "skills" in result:
                merged.skills.extend([SkillGap(**skill) for skill in result["skills"]])
        
        # Calculate final score
        scores = [r.get("score", 50) for r in results if "score" in r]
        if scores:
            merged.score = sum(scores) // len(scores)
        
        return merged

# Global parser instance
response_parser = ResponseParser()
