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
      "file": "filename",
      "lines": "start-end",
      "snippet": "exact code excerpt",
      "problem": "clear technical explanation",
      "impact": "why it matters",
      "fix": "concrete improvement suggestion"
    }}
  ],
  "score": 85
}}

CRITICAL REQUIREMENTS:
- EVERY issue MUST include: file, lines, snippet, problem, impact, fix
- Use "Not available" only if you cannot determine the field
- snippet must be exact code from the provided chunks
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the technical issue clearly
- impact must explain why this matters for the codebase
- fix must provide actionable improvement steps

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
      "file": "filename",
      "lines": "start-end",
      "snippet": "exact code excerpt",
      "problem": "clear technical explanation",
      "impact": "why it matters",
      "fix": "concrete improvement suggestion",
      "cwe": "CWE-ID"
    }}
  ],
  "score": 90
}}

CRITICAL REQUIREMENTS:
- EVERY security issue MUST include: file, lines, snippet, problem, impact, fix
- Use "Not available" only if you cannot determine the field
- snippet must be exact code from the provided chunks
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the security vulnerability clearly
- impact must explain why this is a security risk
- fix must provide actionable security improvement steps
- cwe should be the relevant CWE identifier if known

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
      "file": "filename",
      "lines": "start-end",
      "snippet": "exact code excerpt",
      "problem": "clear technical explanation",
      "impact": "why it matters",
      "fix": "concrete improvement suggestion",
      "principle": "SOLID/Dry/Kiss/etc"
    }}
  ],
  "score": 80
}}

CRITICAL REQUIREMENTS:
- EVERY architecture issue MUST include: file, lines, snippet, problem, impact, fix
- Use "Not available" only if you cannot determine the field
- snippet must be exact code from the provided chunks
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the architectural issue clearly
- impact must explain why this affects the architecture
- fix must provide actionable architectural improvement steps
- principle should reference relevant architectural principles

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
      "file": "filename",
      "lines": "start-end",
      "snippet": "exact code excerpt",
      "gap": "What's missing or could improve",
      "impact": "why it matters",
      "resource": "Learning resource suggestion",
      "priority": "low|medium|high"
    }}
  ],
  "score": 75
}}

CRITICAL REQUIREMENTS:
- EVERY skill gap MUST include: file, lines, snippet, gap, impact, resource
- Use "Not available" only if you cannot determine the field
- snippet must be exact code from the provided chunks
- lines must be "start-end" format (e.g., "15-22")
- gap must explain what skill is missing or could improve
- impact must explain why this skill matters for the codebase
- resource must provide specific learning resource suggestions
- priority indicates urgency of learning this skill

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
