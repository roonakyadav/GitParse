# Phase 3: AI Review Engine

## Overview

Phase 3 extends RepoMind with AI-powered code review capabilities using the Groq API. It analyzes processed code chunks from Phase 2 and generates comprehensive insights about code quality, security, architecture, and skill gaps.

## Architecture

### Core Components

- **`ai/client.py`** - Groq API client with key rotation and retry logic
- **`ai/prompts.py`** - Structured prompt templates for different review types
- **`ai/parser.py`** - JSON response parsing and validation with Pydantic models
- **`ai/reviewer.py`** - Main review engine pipeline
- **`ai/__init__.py`** - Module exports and lazy client initialization

### API Endpoints

- **`POST /api/review`** - Analyze Phase 2 output and return AI insights
- **`GET /`** - Root endpoint showing Phase 3 status
- **`GET /health`** - Health check endpoint

## Configuration

### Environment Variables

```bash
# Option 1: Single API key
GROQ_API_KEY=your_groq_api_key_here

# Option 2: Multiple API keys for rotation (recommended)
GROQ_KEYS=key1,key2,key3

# Groq Model (optional, defaults to llama3-70b-8192)
GROQ_MODEL=llama3-70b-8192
```

## Features

### Review Types

1. **Quality Review** - Code readability, performance, error handling, duplication
2. **Security Review** - SQL injection, XSS, authentication flaws, data exposure
3. **Architecture Review** - SOLID principles, coupling, design patterns, scalability
4. **Skills Review** - Learning gaps, modern practices, framework usage, testing

### Performance Features

- **Chunk Selection** - Intelligently selects most important code chunks
- **Batch Processing** - Processes up to 10 chunks per request
- **Caching** - Local memory cache with 1-hour TTL
- **Key Rotation** - Automatic API key rotation for rate limit management
- **Retry Logic** - 3-retry policy with exponential backoff

## Response Format

```json
{
  "issues": [
    {
      "type": "quality",
      "severity": "medium",
      "message": "Function lacks error handling",
      "file": "utils.py",
      "line": 25,
      "suggestion": "Add try-catch block"
    }
  ],
  "security": [...],
  "architecture": [...],
  "skills": [...],
  "score": 75,
  "chunks_analyzed": 15,
  "total_chunks": 45,
  "review_types": ["quality", "security", "architecture", "skills"]
}
```

## Usage

### Direct API Usage

```python
import requests

# Phase 2 output (simplified)
phase2_data = {
    "chunks": [
        {
            "content": "def hello_world():\n    print('Hello')",
            "file": "main.py",
            "start_line": 1,
            "token_count": 15,
            "dependencies": []
        }
    ]
}

# Get AI review
response = requests.post("http://localhost:8000/api/review", json=phase2_data)
result = response.json()

print(f"Overall Score: {result['score']}")
print(f"Issues Found: {len(result['issues'])}")
```

### Using the Review Engine Directly

```python
import asyncio
from ai.reviewer import review_engine

async def analyze_code():
    result = await review_engine.analyze_repo(phase2_data)
    return result

# Run analysis
result = asyncio.run(analyze_code())
```

## Testing

Run the comprehensive test suite:

```bash
source venv/bin/activate
python -m pytest test_ai.py -v
```

Tests cover:
- Groq client functionality and key rotation
- Prompt template generation
- JSON parsing and validation
- Review engine pipeline
- Caching mechanisms
- Error handling

## Constraints Met

✅ **No OpenAI** - Uses only Groq API
✅ **No LangChain** - Direct HTTP client implementation
✅ **No paid SDKs** - Uses only open-source dependencies
✅ **No vector DB** - Simple caching with in-memory storage
✅ **Phase 2 Compatible** - Works with existing Phase 2 output format
✅ **Rate Limit Respected** - Key rotation and retry logic
✅ **Structured Output** - Validated JSON responses with Pydantic

## Dependencies

All dependencies are already included in `requirements.txt`:
- `httpx` - Async HTTP client for Groq API
- `pydantic` - Data validation and parsing
- Existing Phase 2 dependencies

## Error Handling

The system gracefully handles:
- Invalid API keys with automatic rotation
- Rate limits with exponential backoff
- Network timeouts with retries
- Malformed LLM responses with fallbacks
- Missing configuration with clear error messages

## Performance

- **Max chunks per request**: 10
- **Concurrent review types**: 4 (quality, security, architecture, skills)
- **Cache TTL**: 1 hour
- **Timeout**: 30 seconds per request
- **Max retries**: 3 per request

## Next Steps

To use Phase 3 in production:

1. Set up Groq API keys in environment
2. Configure rate limits and monitoring
3. Add frontend integration at `/review` route
4. Set up logging and alerting
5. Consider persistent caching for large repositories
