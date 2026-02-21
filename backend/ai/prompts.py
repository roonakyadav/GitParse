"""Prompt templates for AI code review."""

# Shared system prompt for all reviews
SYSTEM_PROMPT = """You are a senior code reviewer. Analyze the given code and return ONLY valid JSON.
No explanations, no markdown, no prose outside the JSON structure.
Any text outside JSON is invalid and will be rejected.
Follow the exact schema specified in each prompt."""

QUALITY_REVIEW_TEMPLATE = """{system_prompt}

Analyze the following code chunks for quality issues.

Code chunks:
{{chunks}}

You MUST return ONLY this exact JSON structure:
{{
  "issues": [
    {{
      "type": "quality",
      "severity": "low|medium|high|critical",
      "message": "Brief description of issue",
      "file": "filename",
      "line": 123,
      "suggestion": "How to fix it"
    }}
  ],
  "score": 85
}}

Focus on:
- Code readability and maintainability
- Performance bottlenecks
- Error handling
- Code duplication
- Naming conventions
- Documentation gaps

Return ONLY JSON. No other text."""

SECURITY_REVIEW_TEMPLATE = """{system_prompt}

Analyze the following code chunks for security vulnerabilities.

Code chunks:
{{chunks}}

You MUST return ONLY this exact JSON structure:
{{
  "security": [
    {{
      "type": "security",
      "severity": "low|medium|high|critical",
      "message": "Security issue description",
      "file": "filename",
      "line": 123,
      "cwe": "CWE-ID",
      "suggestion": "Security fix recommendation"
    }}
  ],
  "score": 90
}}

Focus on:
- SQL injection
- XSS vulnerabilities
- Authentication/authorization flaws
- Sensitive data exposure
- Input validation
- Cryptographic issues
- Dependency vulnerabilities

Return ONLY JSON. No other text."""

ARCHITECTURE_REVIEW_TEMPLATE = """{system_prompt}

Analyze the following code chunks for architectural issues.

Code chunks:
{{chunks}}

You MUST return ONLY this exact JSON structure:
{{
  "architecture": [
    {{
      "type": "architecture",
      "severity": "low|medium|high|critical",
      "message": "Architectural concern",
      "file": "filename",
      "line": 123,
      "principle": "SOLID/Dry/Kiss/etc",
      "suggestion": "Architectural improvement"
    }}
  ],
  "score": 80
}}

Focus on:
- SOLID principles violations
- Tight coupling
- Separation of concerns
- Design patterns misuse
- Scalability issues
- Code organization
- Module dependencies

Return ONLY JSON. No other text."""

LEARNING_ADVICE_TEMPLATE = """{system_prompt}

Analyze the following code chunks and provide learning advice.

Code chunks:
{{chunks}}

You MUST return ONLY this exact JSON structure:
{{
  "skills": [
    {{
      "category": "language|framework|pattern|tool",
      "skill": "Specific skill name",
      "level": "beginner|intermediate|advanced",
      "gap": "What's missing or could improve",
      "resource": "Learning resource suggestion",
      "priority": "low|medium|high"
    }}
  ],
  "score": 75
}}

Focus on:
- Modern language features
- Best practices
- Design patterns
- Framework usage
- Testing approaches
- Performance optimization
- Code organization

Return ONLY JSON. No other text."""

def get_prompt_template(review_type: str) -> str:
    """Get prompt template by review type."""
    templates = {
        "quality": QUALITY_REVIEW_TEMPLATE,
        "security": SECURITY_REVIEW_TEMPLATE,
        "architecture": ARCHITECTURE_REVIEW_TEMPLATE,
        "skills": LEARNING_ADVICE_TEMPLATE
    }
    
    if review_type not in templates:
        raise ValueError(f"Unknown review type: {review_type}")
    
    # Only format system prompt for now, chunks will be formatted separately
    return templates[review_type].format(system_prompt=SYSTEM_PROMPT)

def format_chunks_for_prompt(chunks: list, max_chunks: int = 10) -> str:
    """Format code chunks for prompt input."""
    selected_chunks = chunks[:max_chunks]
    
    formatted = []
    for i, chunk in enumerate(selected_chunks, 1):
        chunk_text = chunk.get("content", "").strip()
        if len(chunk_text) > 2000:
            chunk_text = chunk_text[:2000] + "..."
        
        formatted.append(f"Chunk {i} ({chunk.get('file', 'unknown')}:{chunk.get('start_line', '?')}):\n{chunk_text}")
    
    return "\n\n".join(formatted)
