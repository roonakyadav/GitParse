import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
import os

# ensure httpx is available or skip entire AI tests module since the client
# depends on it at import time
httpx = pytest.importorskip('httpx')

# Set environment variables before importing AI modules
os.environ['GROQ_KEYS'] = 'test_key1,test_key2'

from ai.client import get_groq_client, GroqClient
from ai.parser import ResponseParser
from ai.reviewer import ReviewEngine


class TestEdgeCases:
    """Test edge cases and error scenarios for AI components."""
    
    @pytest.fixture
    def parser(self):
        return ResponseParser()
    
    @pytest.fixture
    def engine(self):
        return ReviewEngine()
    
    @pytest.fixture
    def client(self):
        return GroqClient()
    
    def test_malformed_json_responses(self, parser):
        """Test parsing various malformed JSON responses."""
        test_cases = [
            # JSON with extra text
            '{"test": "value"} some extra text',
            # JSON in markdown
            'Here is the analysis:\n```json\n{"test": "value"}\n```\nThat\'s all.',
            # Partial JSON
            '{"test": "value", "incomplete": ',
            # Multiple JSON objects
            '{"first": {"nested": true}} {"second": "value"}',
            # JSON with comments (invalid but common)
            '{"test": "value", /* comment */ "other": "data"}',
            # JSON with trailing comma
            '{"test": "value", "other": "data",}',
        ]
        
        for response in test_cases:
            result = parser.extract_json_from_response(response)
            # Should extract some valid JSON or return None
            assert result is None or isinstance(result, dict)
    
    def test_partial_json_reconstruction(self, parser):
        """Test partial JSON reconstruction from malformed responses."""
        response = '''
        The analysis shows some issues:
        "severity": "high",
        "message": "SQL injection vulnerability found",
        "file": "database.py",
        But the JSON is malformed.
        '''
        
        result = parser._reconstruct_partial_json(response)
        assert isinstance(result, dict)
        assert "score" in result
        # Should detect the high severity and adjust score
        assert result["score"] < 75
    
    def test_empty_and_null_responses(self, parser):
        """Test handling of empty and null responses."""
        test_cases = [
            "",
            "   ",
            "[]",
            "{}",
            "null",
            "No analysis available",
        ]
        
        for response in test_cases:
            result = parser.extract_json_from_response(response)
            # Should handle gracefully
            assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_groq_client_model_fallback(self, client):
        """Test model fallback when primary model fails."""
        # Mock a 404 response for primary model
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        
        # Mock success for fallback model
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "Success with fallback"}}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                mock_response_404,  # Primary model fails
                mock_response_200   # Fallback succeeds
            ]
            
            # Set up available models to include fallback
            client.available_models = ["llama3-8b-8192"]  # Fallback model
            
            result = await client.call_groq("test prompt", "invalid_model")
            assert result == "Success with fallback"
    
    @pytest.mark.asyncio
    async def test_groq_client_rate_limit_handling(self, client):
        """Test rate limit handling with retry-after header."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"retry-after": "2"}
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "Success after rate limit"}}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                mock_response_429,  # Rate limited
                mock_response_200   # Success after wait
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await client.call_groq("test prompt")
                assert result == "Success after rate limit"
                mock_sleep.assert_called_with(2)  # Should wait retry-after seconds
    
    @pytest.mark.asyncio
    async def test_heuristic_analysis_quality(self, engine):
        """Test heuristic analysis for quality issues."""
        chunks = [
            {
                "content": "def very_long_function():\n    # TODO: implement this\n    # FIXME: this is broken\n    pass\n" * 20,  # Long function
                "file": "test.py",
                "start_line": 1
            },
            {
                "content": "def another_function():\n    result = risky_operation()\n    return result",  # No error handling
                "file": "test.py",
                "start_line": 25
            }
        ]
        
        result = engine._heuristic_analysis(chunks, "quality")
        
        assert "issues" in result
        assert "score" in result
        assert len(result["issues"]) > 0
        
        # Should detect TODO comments
        todo_issues = [i for i in result["issues"] if "TODO" in i["message"]]
        assert len(todo_issues) > 0
        
        # Should detect long function
        long_func_issues = [i for i in result["issues"] if "long" in i["message"].lower()]
        assert len(long_func_issues) > 0
    
    @pytest.mark.asyncio
    async def test_heuristic_analysis_security(self, engine):
        """Test heuristic analysis for security issues."""
        chunks = [
            {
                "content": 'query = "SELECT * FROM users WHERE id=" + user_id\ncursor.execute(query)',
                "file": "database.py",
                "start_line": 1
            },
            {
                "content": 'password = "secret123"\napi_key = "hardcoded_key"',
                "file": "config.py",
                "start_line": 1
            },
            {
                "content": 'eval(user_input)',
                "file": "dangerous.py",
                "start_line": 1
            }
        ]
        
        result = engine._heuristic_analysis(chunks, "security")
        
        assert "security" in result
        assert "score" in result
        assert len(result["security"]) >= 2  # Should find multiple issues
        
        # Should detect SQL injection
        sql_issues = [i for i in result["security"] if "SQL" in i["message"]]
        assert len(sql_issues) > 0
        
        # Should detect hardcoded credentials
        cred_issues = [i for i in result["security"] if "hardcoded" in i["message"]]
        assert len(cred_issues) > 0
        
        # Score should be low due to critical issues
        assert result["score"] < 50
    
    @pytest.mark.asyncio
    async def test_heuristic_analysis_architecture(self, engine):
        """Test heuristic analysis for architectural issues."""
        chunks = []
        
        # Create many files to trigger modularity warning
        for i in range(25):
            chunks.append({
                "content": f"def function_{i}():\n    pass",
                "file": f"file_{i}.py",
                "start_line": 1,
                "dependencies": [f"dep_{j}" for j in range(15)]  # Many dependencies
            })
        
        result = engine._heuristic_analysis(chunks, "architecture")
        
        assert "architecture" in result
        assert "score" in result
        assert len(result["architecture"]) > 0
        
        # Should detect too many files
        file_issues = [i for i in result["architecture"] if "files" in i["message"]]
        assert len(file_issues) > 0
        
        # Should detect high coupling
        coupling_issues = [i for i in result["architecture"] if "coupling" in i["message"]]
        assert len(coupling_issues) > 0
    
    @pytest.mark.asyncio
    async def test_heuristic_analysis_skills(self, engine):
        """Test heuristic analysis for skill gaps."""
        chunks = [
            {
                "content": "class MyClass:\n    def __init__(self):\n        pass",
                "file": "test.py",
                "start_line": 1
            },
            {
                "content": "const Component = () => {\n    return <div>Hello</div>;\n}",
                "file": "component.jsx",
                "start_line": 1
            }
        ]
        
        result = engine._heuristic_analysis(chunks, "skills")
        
        assert "skills" in result
        assert "score" in result
        
        # Should detect Python OOP
        python_skills = [s for s in result["skills"] if s["category"] == "language" and "Python" in s["skill"]]
        assert len(python_skills) > 0
        
        # Should detect React (or at least some framework skill)
        framework_skills = [s for s in result["skills"] if s["category"] == "framework"]
        assert len(framework_skills) > 0
    
    @pytest.mark.asyncio
    async def test_min_chunk_selection(self, engine):
        """Test chunk selection with minimum chunk requirement."""
        # Test with less than 5 chunks
        chunks = [
            {"content": "chunk1", "file": "file1.py", "token_count": 10},
            {"content": "chunk2", "file": "file2.py", "token_count": 15},
            {"content": "chunk3", "file": "file3.py", "token_count": 20}
        ]
        
        index_data = {"chunks": chunks}
        selected = engine._select_important_chunks(index_data)
        
        # Should return all chunks when less than minimum
        assert len(selected) == 3
    
    @pytest.mark.asyncio
    async def test_review_pipeline_fallback(self, engine):
        """Test review pipeline fallback to heuristic analysis."""
        chunks = [
            {
                "content": "def test_function():\n    # TODO: implement\n    pass",
                "file": "test.py",
                "start_line": 1
            }
        ]
        
        # Mock Groq client to raise exception
        with patch('ai.client.get_groq_client') as mock_client:
            mock_client.return_value.call_groq.side_effect = Exception("API failed")
            
            result = await engine._analyze_single_review(chunks, "quality")
            
            # Should fallback to heuristic analysis
            assert "issues" in result
            assert "score" in result
            assert result["score"] != 50  # Should not be default score
    
    def test_config_validation(self):
        """Test configuration validation."""
        from config import validate_config
        
        # Test with valid config
        with patch.dict('os.environ', {
            'GROQ_KEYS': 'gsk_test_key1,gsk_test_key2',
            'GROQ_MODEL': 'llama3-8b-8192'
        }):
            try:
                validate_config()  # Should not raise
            except Exception:
                pytest.fail("Valid config should not raise exception")
        
        # Test with invalid model
        with patch.dict('os.environ', {
            'GROQ_KEYS': 'gsk_test_key',
            'GROQ_MODEL': 'invalid-model'
        }):
            try:
                validate_config()  # Should warn but not raise
            except Exception:
                pytest.fail("Invalid model should warn but not raise")
        
        # Test with missing keys - should raise ValueError
        with patch.dict('os.environ', {'GROQ_KEYS': '', 'GROQ_API_KEY': ''}, clear=True):
            with pytest.raises(ValueError):
                validate_config()  # Should raise for missing keys
    
    def test_prompt_template_formatting(self):
        """Test prompt template formatting with system prompt."""
        from ai.prompts import get_prompt_template
        
        template = get_prompt_template("quality")
        
        # Should include system prompt
        assert "You are a senior code reviewer" in template
        assert "ONLY valid JSON" in template
        assert "No explanations" in template
        
        # Should format correctly with chunks placeholder
        assert "{chunks}" in template
        assert "You MUST return ONLY this exact JSON structure" in template


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
