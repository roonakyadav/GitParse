import re
import httpx
import logging
from typing import List, Optional, Dict, Any
from config import GITHUB_TOKEN, GITHUB_API_BASE, MAX_FILE_SIZE, REQUEST_TIMEOUT
from schemas import RepoFile

logger = logging.getLogger(__name__)


def parse_repo_url(url: str) -> Optional[tuple]:
    """Parse GitHub repo URL and return (owner, repo) tuple."""
    patterns = [
        r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
        r'github\.com/([^/]+)/([^/]+)/tree/[^/]+/?.*$',
        r'github\.com/([^/]+)/([^/]+)/blob/[^/]+/?.*$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner, repo = match.groups()
            return owner, repo
    
    return None


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.c': 'c',
        '.go': 'golang',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.m': 'objective-c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.fish': 'shell',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.xml': 'xml',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.md': 'markdown',
        '.txt': 'text',
        '.dockerfile': 'dockerfile',
        '.gitignore': 'gitignore',
        '.eslintrc': 'eslint',
        '.prettierrc': 'prettier'
    }
    
    # Extract extension
    if '.' in file_path:
        ext = '.' + file_path.split('.')[-1].lower()
        return extension_map.get(ext, 'text')
    
    return 'text'


def should_ignore_file(file_path: str, size: int) -> bool:
    """Check if file should be ignored based on path and size."""
    ignore_patterns = [
        'node_modules/',
        '.git/',
        'dist/',
        'build/',
        '__pycache__/',
        '.env',
        '.lock',
        '.png',
        '.jpg',
        '.jpeg',
        '.gif',
        '.bmp',
        '.svg',
        '.mp4',
        '.avi',
        '.mov',
        '.zip',
        '.tar',
        '.gz',
        '.rar',
        '.7z',
        '.pdf',
        '.doc',
        '.docx',
        '.xls',
        '.xlsx',
        '.ppt',
        '.pptx'
    ]
    
    # Check size limit
    if size > MAX_FILE_SIZE:
        return True
    
    # Check ignore patterns
    for pattern in ignore_patterns:
        if pattern in file_path.lower():
            return True
    
    return False


async def fetch_repo_tree(owner: str, repo: str) -> List[Dict[str, Any]]:
    """Fetch repository tree from GitHub API."""
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
        logger.info(f"Using GitHub token for {owner}/{repo}")
    else:
        logger.warning(f"No GitHub token configured for {owner}/{repo}. Using anonymous access with rate limits.")
        
    # Add User-Agent header to comply with GitHub API requirements
    headers['User-Agent'] = 'RepoMind-Analyzer/1.0'
    
    timeout = httpx.Timeout(REQUEST_TIMEOUT)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Get default branch
            repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
            logger.info(f"Fetching repository info from {repo_url}")
            
            response = await client.get(repo_url, headers=headers)
            
            if response.status_code == 404:
                raise ValueError("Repository not found or private")
            elif response.status_code == 403 or response.status_code == 429:
                # Check if it's a rate limit issue
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
                if 'rate limit' in response.text.lower() or 'limit exceeded' in response.text.lower() or rate_limit_remaining == '0':
                    raise ValueError("GitHub rate limit exceeded. Please configure GITHUB_TOKEN.")
                else:
                    raise ValueError("Access forbidden. Repository may be private.")
            elif response.status_code != 200:
                raise ValueError(f"Failed to fetch repository info: {response.status_code} - {response.text}")
            
            repo_data = response.json()
            default_branch = repo_data.get('default_branch', 'main')
            logger.info(f"Default branch: {default_branch}")
            
            # Get tree
            tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            logger.info(f"Fetching tree from {tree_url}")
            
            response = await client.get(tree_url, headers=headers)
            
            if response.status_code == 403 or response.status_code == 429:
                # Check if it's a rate limit issue
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', '0')
                if 'rate limit' in response.text.lower() or 'limit exceeded' in response.text.lower() or rate_limit_remaining == '0':
                    raise ValueError("GitHub rate limit exceeded. Please configure GITHUB_TOKEN.")
                else:
                    raise ValueError("Access forbidden while fetching tree.")
            elif response.status_code != 200:
                raise ValueError(f"Failed to fetch tree: {response.status_code} - {response.text}")
            
            tree_data = response.json()
            tree_items = tree_data.get('tree', [])
            logger.info(f"Fetched {len(tree_items)} items from repository tree")
            
            # Check if tree was truncated
            if tree_data.get('truncated', False):
                logger.warning("Repository tree was truncated due to size. Some files may be missing.")
            
            return tree_items
            
    except httpx.TimeoutException:
        raise ValueError("Request timeout. Repository may be too large or network is slow.")
    except httpx.RequestError as e:
        raise ValueError(f"Network error: {str(e)}")


async def process_repo_files(owner: str, repo: str) -> List[RepoFile]:
    """Process repository files and return filtered list."""
    logger.info(f"Processing files for {owner}/{repo}")
    tree = await fetch_repo_tree(owner, repo)
    files = []
    ignored_count = 0
    
    for item in tree:
        if item['type'] != 'blob':
            continue
        
        file_path = item['path']
        size = item['size']
        
        if should_ignore_file(file_path, size):
            ignored_count += 1
            continue
        
        language = detect_language(file_path)
        download_url = item['url']
        
        files.append(RepoFile(
            path=file_path,
            size=size,
            language=language,
            download_url=download_url
        ))
    
    logger.info(f"Processed {len(tree)} items: {len(files)} files included, {ignored_count} files ignored")
    return files
