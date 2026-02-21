import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
import os

# ensure httpx is available or skip relevant tests
httpx = pytest.importorskip('httpx')

# Set environment variables before importing AI modules
os.environ['GROQ_KEYS'] = 'test_key1,test_key2'

from ai.client import GroqClient
from ai.prompts import get_prompt_template, format_chunks_for_prompt
from ai.parser import ResponseParser, Issue, SecurityIssue, ArchitectureIssue, SkillGap
from ai.reviewer import ReviewEngine


class TestGroqClient:
    @pytest.fixture
    def client(self):
        with patch.dict('os.environ', {'GROQ_KEYS': 'key1,key2,key3'}):
            return GroqClient()
    
    def test_parse_api_keys_single(self):
        with patch.dict('os.environ', {'GROQ_KEYS': 'single_key'}):
            client = GroqClient()
            assert len(client.api_keys) == 1
            assert client.api_keys[0] == 'single_key'
    
    def test_parse_api_keys_multiple(self):
        with patch.dict('os.environ', {'GROQ_KEYS': 'key1,key2,key3'}):
            client = GroqClient()
            assert len(client.api_keys) == 3
            assert client.api_keys == ['key1', 'key2', 'key3']
    
    def test_parse_api_keys_fallback(self):
        with patch('ai.client.GROQ_API_KEY', 'fallback_key'):
            with patch.dict('os.environ', {'GROQ_KEYS': ''}, clear=False):
                client = GroqClient()
                assert len(client.api_keys) == 1
                assert client.api_keys[0] == 'fallback_key'
    
    def test_key_rotation(self, client):
        initial_index = client.current_key_index
        key1 = client._get_current_key()
        key2 = client._get_current_key()
        
        assert key1 != key2
        assert client.current_key_index == initial_index + 2
    
    @pytest.mark.asyncio
    async def test_call_groq_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await client.call_groq("test prompt")
            assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_call_groq_retry_on_401(self, client):
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "Success after retry"}}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                mock_response_401,
                mock_response_200
            ]
            
            result = await client.call_groq("test prompt")
            assert result == "Success after retry"


class TestPrompts:
    def test_get_prompt_template(self):
        template = get_prompt_template("quality")
        assert "quality issues" in template.lower()
        
        template = get_prompt_template("security")
        assert "security vulnerabilities" in template.lower()
        
        with pytest.raises(ValueError):
            get_prompt_template("unknown")
    
    def test_format_chunks_for_prompt(self):
        chunks = [
            {"content": "def test(): pass", "file": "test.py", "start_line": 1},
            {"content": "class Test: pass", "file": "test.py", "start_line": 3}
        ]
        
        result = format_chunks_for_prompt(chunks)
        assert "Chunk 1" in result
        assert "test.py:1" in result
        assert "def test(): pass" in result
    
    def test_format_chunks_truncates_long_content(self):
        long_content = "x" * 3000
        chunks = [{"content": long_content, "file": "test.py", "start_line": 1}]
        
        result = format_chunks_for_prompt(chunks)
        assert "..." in result
        assert len(result) < len(long_content) + 100


class TestResponseParser:
    @pytest.fixture
    def parser(self):
        return ResponseParser()
    
    def test_extract_json_valid(self, parser):
        response = '{"test": "value"}'
        result = parser.extract_json_from_response(response)
        assert result == {"test": "value"}
    
    def test_extract_json_from_markdown(self, parser):
        response = '```json\n{"test": "value"}\n```'
        result = parser.extract_json_from_response(response)
        assert result == {"test": "value"}
    
    def test_extract_json_finds_object_in_text(self, parser):
        response = 'Some text {"test": "value"} more text'
        result = parser.extract_json_from_response(response)
        assert result == {"test": "value"}
    
    def test_extract_json_invalid_returns_none(self, parser):
        response = 'invalid json'
        result = parser.extract_json_from_response(response)
        assert result is None
    
    def test_parse_quality_review(self, parser):
        data = {
            "issues": [
                {
                    "type": "quality",
                    "severity": "medium",
                    "message": "Test issue",
                    "file": "test.py",
                    "line": 10,
                    "suggestion": "Fix it"
                }
            ],
            "score": 85
        }
        
        result = parser.parse_review_response(data, "quality")
        assert len(result["issues"]) == 1
        assert result["score"] == 85
        assert result["issues"][0]["message"] == "Test issue"
    
    def test_parse_security_review(self, parser):
        data = {
            "security": [
                {
                    "type": "security",
                    "severity": "high",
                    "message": "SQL injection",
                    "file": "db.py",
                    "line": 25,
                    "cwe": "CWE-89",
                    "suggestion": "Use parameterized queries"
                }
            ],
            "score": 70
        }
        
        result = parser.parse_review_response(data, "security")
        assert len(result["security"]) == 1
        assert result["security"][0]["cwe"] == "CWE-89"
    
    def test_merge_results(self, parser):
        results = [
            {"issues": [{"type": "quality", "severity": "medium", "message": "Issue 1", "file": "test.py", "line": 1, "suggestion": "Fix"}], "score": 80},
            {"security": [{"type": "security", "severity": "high", "message": "Issue 2", "file": "test.py", "line": 2, "suggestion": "Fix"}], "score": 70}
        ]
        
        merged = parser.merge_results(results)
        assert len(merged.issues) == 1
        assert len(merged.security) == 1
        assert merged.score == 75  # Average of 80 and 70


class TestReviewEngine:
    @pytest.fixture
    def engine(self):
        return ReviewEngine()
    
    def test_select_important_chunks(self, engine):
        index_data = {
            "chunks": [
                {"content": "small", "file": "util.py", "token_count": 10},
                {"content": "def main(): pass", "file": "main.py", "token_count": 100, "dependencies": ["util"]},
                {"content": "class BigClass: pass", "file": "models.py", "token_count": 200}
            ]
        }
        
        selected = engine._select_important_chunks(index_data, max_chunks=2)
        # With minimum chunk logic, if total chunks < 5, it returns all chunks
        assert len(selected) == 3  # All chunks returned since < 5 minimum
        # Should prefer chunks with higher scores
        assert any(chunk["file"] == "models.py" for chunk in selected)
        assert any(chunk["file"] == "main.py" for chunk in selected)
    
    def test_get_cache_key(self, engine):
        chunks1 = [{"content": "test"}]
        chunks2 = [{"content": "test"}]
        chunks3 = [{"content": "different"}]
        
        key1 = engine._get_cache_key(chunks1, "quality")
        key2 = engine._get_cache_key(chunks2, "quality")
        key3 = engine._get_cache_key(chunks3, "quality")
        key4 = engine._get_cache_key(chunks1, "security")
        
        assert key1 == key2  # Same content and type
        assert key1 != key3  # Different content
        assert key1 != key4  # Different type
    
    @pytest.mark.asyncio
    async def test_analyze_single_review_cached(self, engine):
        chunks = [{"content": "test"}]
        
        # Mock the cache to return a result directly
        cache_key = engine._get_cache_key(chunks, "quality")
        engine.cache[cache_key] = ({"issues": [], "score": 90}, time.time())
        
        # Mock the analyze method to check cache first
        with patch.object(engine, '_is_cache_valid', return_value=True):
            result = await engine._analyze_single_review(chunks, "quality")
            assert result["score"] == 90
    
    @pytest.mark.asyncio
    async def test_analyze_repo_no_chunks(self, engine):
        index_data = {"chunks": []}
        
        result = await engine.analyze_repo(index_data)
        assert "error" in result
        assert result["score"] == 50
    
    @pytest.mark.asyncio
    async def test_analyze_repo_success(self, engine):
        index_data = {
            "chunks": [
                {"content": "def test(): pass", "file": "test.py", "token_count": 50}
            ]
        }
        
        # Mock the review methods
        with patch.object(engine, '_analyze_single_review') as mock_analyze:
            mock_analyze.return_value = {"score": 80}
            
            result = await engine.analyze_repo(index_data)
            
            assert "score" in result
            assert "chunks_analyzed" in result
            assert "review_types" in result
            assert mock_analyze.call_count == 4  # quality, security, architecture, skills


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
