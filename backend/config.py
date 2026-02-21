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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# API configuration
GITHUB_API_BASE = "https://api.github.com"
MAX_FILE_SIZE = 500 * 1024  # 500KB
REQUEST_TIMEOUT = 30  # seconds

# Log configuration status
if GITHUB_TOKEN:
    logger.info("GitHub token found in environment")
else:
    logger.info("No GitHub token found - using anonymous access (rate limited)")
