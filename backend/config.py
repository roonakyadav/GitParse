import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_KEYS = os.getenv("GROQ_KEYS", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# API configuration
GITHUB_API_BASE = "https://api.github.com"
MAX_FILE_SIZE = 500 * 1024  # 500KB
REQUEST_TIMEOUT = 30  # seconds

def validate_config():
    """Validate configuration at startup."""
    errors = []
    warnings = []
    
    # Validate Groq configuration
    groq_keys = GROQ_KEYS or GROQ_API_KEY
    if not groq_keys:
        errors.append("No Groq API keys found. Set GROQ_KEYS or GROQ_API_KEY environment variable.")
    else:
        # Check key format
        keys_list = [key.strip() for key in groq_keys.split(",") if key.strip()]
        if not keys_list:
            errors.append("Invalid Groq API keys format.")
        else:
            logger.info(f"Found {len(keys_list)} Groq API key(s)")
            
            # Check key format (basic validation)
            for key in keys_list:
                if not key.startswith("gsk_"):
                    warnings.append(f"Groq API key may be invalid (doesn't start with 'gsk_'): {key[:8]}...")
    
    # Validate Groq model
    valid_models = ["llama3-8b-8192", "mixtral-8x7b-32768", "llama3-70b-8192", "llama-3.1-8b-instant", "llama-3.1-70b-versatile"]
    if GROQ_MODEL not in valid_models:
        warnings.append(f"Groq model '{GROQ_MODEL}' may not be supported. Valid models: {valid_models}")
    else:
        logger.info(f"Using Groq model: {GROQ_MODEL}")
    
    # Validate GitHub token (optional)
    if GITHUB_TOKEN:
        if not GITHUB_TOKEN.startswith("ghp_") and not GITHUB_TOKEN.startswith("gho_"):
            warnings.append("GitHub token format may be invalid (doesn't start with 'ghp_' or 'gho_')")
        else:
            logger.info("GitHub token found and format looks valid")
    else:
        logger.info("No GitHub token found - using anonymous access (rate limited)")
    
    # Log validation results
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        raise ValueError("Invalid configuration. See logs for details.")
    
    if warnings:
        logger.warning("Configuration validation warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    logger.info("Configuration validation completed successfully")

# Validate configuration at import time
try:
    validate_config()
except Exception as e:
    logger.error(f"Configuration validation failed: {str(e)}")
    # Don't raise here to allow the application to start with partial functionality
