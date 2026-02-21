"""
Token estimation using tiktoken or fallback word-based counting.

Provides OpenAI-compatible token counting for accurate chunk sizing.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import tiktoken
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
    # Initialize tokenizer (cl100k_base is compatible with most models)
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    TIKTOKEN_AVAILABLE = False
    TOKENIZER = None
    logger.warning("tiktoken not available - using fallback token counting")


def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken or fallback method.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
    
    if TIKTOKEN_AVAILABLE and TOKENIZER:
        try:
            return len(TOKENIZER.encode(text))
        except Exception as e:
            logger.warning(f"tiktoken failed, using fallback: {e}")
            return _fallback_token_count(text)
    else:
        return _fallback_token_count(text)


def _fallback_token_count(text: str) -> int:
    """
    Fallback token counting based on word and character analysis.
    
    This is less accurate than tiktoken but provides reasonable estimates.
    """
    # Basic heuristic: roughly 1 token per 4 characters or per word
    # Adjusted for common programming patterns
    
    # Count words (split on whitespace and punctuation)
    import re
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    
    # Count characters
    char_count = len(text)
    
    # Programming-specific adjustments
    # For code, use a more balanced approach
    # Average token is typically 3-4 characters for code
    
    # More accurate estimation for code
    # Use character-based but adjust for programming patterns
    tokens_by_chars = char_count // 3.5  # More realistic than 4
    tokens_by_words = word_count * 1.2  # Slight adjustment for code
    
    # Take the average for better balance
    estimated_tokens = int((tokens_by_chars + tokens_by_words) / 2)
    
    # Add small buffer but not too much
    return max(1, estimated_tokens)


def estimate_chunk_tokens(chunk: dict) -> int:
    """
    Estimate tokens for a chunk including metadata.
    
    Args:
        chunk: Chunk dictionary with content and metadata
        
    Returns:
        Estimated token count
    """
    content = chunk.get('content', '')
    
    # Base tokens from content
    content_tokens = count_tokens(content)
    
    # Add minimal tokens for metadata (don't overcount)
    # Metadata is usually compact JSON, estimate conservatively
    metadata = chunk.get('metadata', {})
    metadata_tokens = max(5, len(str(metadata)) // 10)  # Much smaller estimate
    
    return content_tokens + metadata_tokens


def validate_chunk_size(chunk: dict, min_tokens: int = 300, max_tokens: int = 800) -> bool:
    """
    Validate if a chunk is within acceptable token limits.
    
    Args:
        chunk: Chunk to validate
        min_tokens: Minimum preferred tokens
        max_tokens: Maximum allowed tokens
        
    Returns:
        True if chunk size is acceptable
    """
    token_count = estimate_chunk_tokens(chunk)
    return min_tokens <= token_count <= max_tokens


def get_tokenizer_info() -> dict:
    """
    Get information about the current tokenizer setup.
    
    Returns:
        Dictionary with tokenizer details
    """
    if TIKTOKEN_AVAILABLE:
        return {
            'method': 'tiktoken',
            'encoding': 'cl100k_base',
            'available': True
        }
    else:
        return {
            'method': 'fallback',
            'description': 'word-based estimation',
            'available': False
        }
