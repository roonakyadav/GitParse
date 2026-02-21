"""Prompt templates for AI code review."""

# Shared system prompt for all reviews
SYSTEM_PROMPT = """You are a senior code reviewer. Analyze the given code and return ONLY valid JSON.
No explanations, no markdown, no prose outside the JSON structure.
Any text outside JSON is invalid and will be rejected.
Follow the exact schema specified in each prompt.

GROUNDING RULES:
- You MUST ONLY reference code provided in chunks below
- NEVER invent examples or code snippets not present in chunks
- All code references must be exact copies from provided chunks
- Every finding MUST include evidence from provided chunks

ANALYSIS EXPECTATION:
- You MUST analyze structure, duplication, naming, complexity, and architectural patterns even if no obvious bug exists
- You may analyze patterns across multiple chunks
- You may infer implications from code structure
- You may identify architectural issues from code organization
- You may suggest improvements based on best practices

MINIMUM OUTPUT REQUIREMENT:
- If the repo truly has minimal issues, return at least minor suggestions
- Avoid returning completely empty arrays
- Always provide some analysis, even if only minor improvements

EVIDENCE REQUIREMENTS:
- Every file reference must exist in provided chunks
- Every line number must be within chunk ranges
- Every code snippet must be exact copy from chunks
- Every finding MUST reference one or more CHUNK_IDs
- Do not return 'Not found in chunks'
- If no specific chunk applies, use chunk_id: "GLOBAL"
"""

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
- snippet must be EXACT code from provided chunks above
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the technical issue clearly
- impact must explain why this matters for the codebase
- fix must provide actionable improvement steps
- When evidence is missing, use 'Not found in chunks'

MANDATORY ANALYSIS AREAS:
- You must analyze structure, duplication, naming, complexity, and architectural patterns
- Look for code readability and maintainability issues
- Identify performance bottlenecks
- Check error handling patterns
- Find code duplication
- Evaluate naming conventions
- Assess documentation gaps
- Identify minor improvements even if no major issues exist

MINIMUM OUTPUT: Return at least 1-2 findings even for clean codebases.

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
- Use "Not found in chunks" only if you cannot determine the field from provided chunks
- snippet must be EXACT code from provided chunks above
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the security vulnerability clearly
- impact must explain why this is a security risk
- fix must provide actionable security improvement steps
- NEVER invent code snippets - use exact copies from chunks
- If no relevant chunk exists, use snippet: "Not found in provided context"
- cwe should be relevant CWE identifier if known

Focus on:
- SQL injection
- XSS vulnerabilities
- Authentication/authorization flaws
- Input validation
- Cryptographic issues
- Dependency vulnerabilities

MINIMUM OUTPUT: Return at least 1-2 findings even for secure codebases.

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
- Use "Not found in chunks" only if you cannot determine the field from provided chunks
- snippet must be EXACT code from provided chunks above
- lines must be "start-end" format (e.g., "15-22")
- problem must explain the architectural issue clearly
- impact must explain why this affects the architecture
- fix must provide actionable architectural improvement steps
- NEVER invent code snippets - use exact copies from chunks
- If no relevant chunk exists, use snippet: "Not found in provided context"
- principle should reference relevant architectural principles

Focus on:
- SOLID principles violations
- Tight coupling
- Separation of concerns
- Design patterns misuse
- Scalability issues
- Code organization
- Module dependencies

MINIMUM OUTPUT: Return at least 1-2 findings even for well-architected codebases.

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
- Use "Not found in chunks" only if you cannot determine the field from provided chunks
- snippet must be EXACT code from provided chunks above
- lines must be "start-end" format (e.g., "15-22")
- gap must explain what skill is missing or could improve
- impact must explain why this skill matters for the codebase
- resource must provide specific learning resource suggestions
- NEVER invent code snippets - use exact copies from chunks
- If no relevant chunk exists, use snippet: "Not found in provided context"
- priority indicates urgency of learning this skill

Focus on:
- Modern language features
- Best practices
- Design patterns
- Framework usage
- Testing approaches
- Performance optimization
- Code organization

MINIMUM OUTPUT: Return at least 1-2 findings even for skilled codebases.

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

def format_chunks_for_prompt(chunks: list, max_chunks: int = 15) -> str:
    """Format code chunks for prompt input with clear delimiters."""
    import logging
    logger = logging.getLogger(__name__)
    
    selected_chunks = chunks[:max_chunks]
    
    # Log debug information about chunks being sent
    logger.info(f"Formatting {len(selected_chunks)} chunks for AI prompt (max_chunks: {max_chunks})")
    
    formatted = []
    for i, chunk in enumerate(selected_chunks, 1):
        chunk_text = chunk.get("content", "").strip()
        
        # Verify chunk has content
        if not chunk_text:
            logger.warning(f"Empty chunk found at position {i}, file: {chunk.get('file_path', 'unknown')} or {chunk.get('file', 'unknown')}")
            continue
        
        if len(chunk_text) > 2000:
            chunk_text = chunk_text[:2000] + "..."
        
        # Create clearly delimited chunk with metadata and unique ID
        # Try both possible field names for file path
        file_path = chunk.get('file_path', chunk.get('file', 'unknown'))
        start_line = chunk.get('start_line', chunk.get('start', '?'))
        end_line = chunk.get('end_line', chunk.get('end', '?'))
        language = chunk.get('language', chunk.get('lang', 'unknown'))
        
        formatted_chunk = f"""[CHUNK_{i}]
FILE: {file_path}
LINES: {start_line}-{end_line}
CODE:\n{chunk_text}

"""
        
        formatted.append(formatted_chunk)
    
    result = "\n\n".join(formatted)
    logger.info(f"Formatted prompt contains {len(result)} characters from {len(formatted)} valid chunks")
    
    return result
