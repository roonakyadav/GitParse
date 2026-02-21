import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from schemas import AnalyzeRequest, RepoAnalysis, ApiError, RepoFile
from github import parse_repo_url, process_repo_files, GitHubRateLimitExceeded, store_repo_snapshot
from processing.indexer import create_repository_index
from ai import review_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RepoMind AI API", 
    version="3.0.0",
    description="GitHub repository analysis API with Phase 2 processing and Phase 3 AI Review Engine"
)

# Configure CORS properly - single middleware instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


@app.post("/api/analyze", response_model=RepoAnalysis)
async def analyze_repository(request: AnalyzeRequest):
    """Analyze a GitHub repository and return file information."""
    logger.info(f"Analyzing repository: {request.repo_url}")
    
    # Parse repository URL
    parsed = parse_repo_url(request.repo_url)
    if not parsed:
        logger.warning(f"Invalid repository URL: {request.repo_url}")
        raise HTTPException(status_code=400, detail="Invalid repository URL")
    
    owner, repo = parsed
    logger.info(f"Parsed repository: owner={owner}, repo={repo}")
    
    try:
        # Process repository files
        files, analysis_mode = await process_repo_files(owner, repo)
        
        # Determine light mode based on the analysis mode
        is_light_mode = analysis_mode in ["light", "fallback"]
        
        result = RepoAnalysis(
            repo=f"{owner}/{repo}",
            files=files,
            light_mode=is_light_mode,  # Add light mode flag to response
            analysis_mode=analysis_mode  # Add analysis mode to response
        )
        
        # Store successful analysis in cache for future fallback
        store_repo_snapshot(owner, repo, files)
        
        logger.info(f"Analysis completed: {len(files)} files found")
        return result
    
    except GitHubRateLimitExceeded as e:
        logger.warning(f"[RATE_LIMIT] GitHub rate limit exceeded: {str(e)}")
        
        # Try to load cached repo snapshot if exists
        from github import get_cached_repo_snapshot
        cached_snapshot = get_cached_repo_snapshot(owner, repo)
        
        if cached_snapshot and cached_snapshot.get('files'):
            logger.info("[FALLBACK] Using cached repo snapshot due to rate limit")
            cached_files = cached_snapshot['files']
            
            result = RepoAnalysis(
                repo=f"{owner}/{repo}",
                files=cached_files,
                light_mode=True,
                analysis_mode="cached"
            )
            
            # Add rate limit information
            result.limited = True
            result.reason = "github_rate_limit"
            result.retry_after = e.reset_time.isoformat()
            
            logger.info(f"[FALLBACK] Returned cached analysis with {len(cached_files)} files due to rate limit")
            return result
        else:
            logger.info("[FALLBACK] No cached snapshot available, creating synthetic fallback analysis")
            # Create synthetic fallback files to ensure we never return empty files
            synthetic_files = [
                RepoFile(
                    path="README.md",
                    size=0,
                    language="markdown",
                    download_url=f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
                ),
                RepoFile(
                    path="package.json",
                    size=0,
                    language="json",
                    download_url=f"https://api.github.com/repos/{owner}/{repo}/contents/package.json"
                ),
                RepoFile(
                    path="requirements.txt",
                    size=0,
                    language="text",
                    download_url=f"https://api.github.com/repos/{owner}/{repo}/contents/requirements.txt"
                )
            ]
            
            result = RepoAnalysis(
                repo=f"{owner}/{repo}",
                files=synthetic_files,
                light_mode=True,
                analysis_mode="fallback"
            )
            
            # Add rate limit information
            result.limited = True
            result.reason = "github_rate_limit"
            result.retry_after = e.reset_time.isoformat()
            
            logger.info("[FALLBACK] Returned synthetic fallback analysis with 3 files due to rate limit")
            return result
    
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/process", response_model=dict)
async def process_repository(request: dict):
    """Process repository with Phase 2 analysis."""
    logger.info(f"Processing repository with Phase 2 analysis")
    
    try:
        # Validate input - should be Phase 1 output
        if not isinstance(request, dict) or 'files' not in request:
            raise HTTPException(status_code=400, detail="Invalid input format. Expected Phase 1 output.")
        
        # Create repository index
        index = create_repository_index(request)
        
        # CRITICAL: Check if chunks were created
        chunks = index.get('chunks', [])
        if not chunks or len(chunks) == 0:
            logger.error("Phase 2 processing produced zero chunks")
            return {
                "success": False,
                "error": "No chunks generated during processing",
                "reason": "All files failed to chunk or repository contains no processable files",
                "total_files": index.get('total_files', 0),
                "processing_stats": index.get('processing_stats', {}),
                "chunks": []
            }
        
        logger.info(f"Phase 2 processing completed: {index['total_files']} files, {index['total_chunks']} chunks")
        
        # Add success flag to response
        index["success"] = True
        return index
    
    except Exception as e:
        logger.error(f"Phase 2 processing failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Processing failed: {str(e)}",
            "chunks": []
        }


@app.post("/api/review", response_model=dict)
async def review_repository(request: dict):
    """Review repository with Phase 3 AI analysis."""
    review_logger = logging.getLogger("ai.review")
    review_logger.info(f"Starting Phase 3 AI review analysis")
    
    try:
        # Strict input validation - must be Phase 2 output
        if not isinstance(request, dict):
            review_logger.error("Invalid input: request is not a dictionary")
            raise HTTPException(status_code=422, detail="Invalid input format. Expected JSON object.")
        
        if 'chunks' not in request:
            review_logger.error("Invalid input: missing 'chunks' field")
            raise HTTPException(status_code=422, detail="Invalid input format. Expected Phase 2 output with 'chunks' field.")
        
        chunks = request.get('chunks', [])
        if not isinstance(chunks, list) or len(chunks) == 0:
            review_logger.error("Empty chunks received - Phase 2 validation failed")
            raise HTTPException(
                status_code=400, 
                detail="No chunks available. Run processing first."
            )
        
        # Validate chunk structure
        valid_chunks = []
        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                review_logger.warning(f"Skipping invalid chunk {i}: not a dictionary")
                continue
            if 'content' not in chunk or not chunk['content'].strip():
                review_logger.warning(f"Skipping empty chunk {i}: no content")
                continue
            valid_chunks.append(chunk)
        
        if not valid_chunks:
            review_logger.error("No valid chunks found for analysis")
            return {
                "success": False,
                "error": "No valid code chunks found for analysis",
                "issues": [],
                "security": [],
                "architecture": [],
                "skills": [],
                "score": 0
            }
        
        review_logger.info(f"Validated {len(valid_chunks)} chunks out of {len(chunks)} total")
        
        # Run AI review analysis
        review_result = await review_engine.analyze_repo(request)
        
        # Ensure proper response structure
        if not isinstance(review_result, dict):
            review_logger.error(f"Invalid review result type: {type(review_result)}")
            return {
                "success": False,
                "error": "AI analysis returned invalid response",
                "issues": [],
                "security": [],
                "architecture": [],
                "skills": [],
                "score": 0
            }
        
        # Add success flag and ensure all required fields exist
        review_result["success"] = True
        for field in ["issues", "security", "architecture", "skills"]:
            if field not in review_result:
                review_result[field] = []
        
        review_logger.info(f"Phase 3 review completed successfully: score {review_result.get('score', 0)}")
        return review_result
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        review_logger.error(f"Phase 3 review failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"AI analysis failed: {str(e)}",
            "issues": [],
            "security": [],
            "architecture": [],
            "skills": [],
            "score": 0
        }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RepoMind AI API is running", 
        "version": "3.0.0",
        "phase": "Phase 3 - AI Review Engine"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for system monitoring."""
    import sys
    from ai.client import get_groq_client
    from processing import indexer
    
    health_status = {
        "backend": "ok",
        "processing": "ok", 
        "review": "ok",
        "model": "ok",
        "version": "3.0.0",
        "phase": "Phase 3"
    }
    
    # Test processing module
    try:
        # Test indexer import
        test_files = [{"path": "test.py", "size": 100, "language": "python", "download_url": ""}]
        index_result = indexer.create_repository_index({"files": test_files, "repo": "test"})
        if not index_result or index_result.get("total_chunks", 0) == 0:
            health_status["processing"] = "warning"
    except Exception as e:
        health_status["processing"] = "error"
    
    # Test review engine
    try:
        # Test review engine import and basic functionality
        from ai import reviewer
        review_engine = reviewer.ReviewEngine()
        if not review_engine:
            health_status["review"] = "error"
    except Exception as e:
        health_status["review"] = "error"
    
    # Test AI model connection
    try:
        client = get_groq_client()
        if not client:
            health_status["model"] = "error"
    except Exception as e:
        health_status["model"] = "error"
    
    # Overall status
    overall_status = "healthy"
    if any(status == "error" for status in health_status.values() if isinstance(status, str)):
        overall_status = "unhealthy"
    elif any(status == "warning" for status in health_status.values() if isinstance(status, str)):
        overall_status = "degraded"
    
    health_status["status"] = overall_status
    return health_status


def _create_review_fallback_chunks(request: dict) -> List[dict]:
    """Create fallback chunks from request data for review analysis."""
    chunks = []
    
    # Try to get files information
    files = request.get('files', [])
    if not files:
        return []
    
    # Create chunks from file information
    content_lines = [
        "# Repository Analysis Summary",
        "# Generated for AI review when normal chunking failed",
        "",
        "## Repository Information:",
        f"- Repository: {request.get('repo', 'Unknown')}",
        f"- Total Files: {len(files)}",
        "",
        "## File Inventory:",
    ]
    
    # Add file information
    for file_info in files[:30]:  # Limit to first 30 files
        file_path = file_info.get('path', 'unknown')
        language = file_info.get('language', 'unknown')
        size = file_info.get('size', 0)
        
        content_lines.extend([
            f"- {file_path} ({language}, {size} bytes)"
        ])
    
    if len(files) > 30:
        content_lines.append(f"- ... and {len(files) - 30} more files")
    
    # Add processing information if available
    if 'processing_stats' in request:
        stats = request['processing_stats']
        content_lines.extend([
            "",
            "## Processing Statistics:",
            f"- Files Processed: {stats.get('files_processed', 0)}",
            f"- Files Failed: {stats.get('files_failed', 0)}",
            f"- Chunks Created: {stats.get('chunks_created', 0)}",
        ])
    
    content_lines.extend([
        "",
        "## Analysis Notes:",
        "- Normal chunking process failed",
        "- This is a fallback analysis based on file metadata",
        "- Consider manual review of the repository",
        "",
        "## Recommendations:",
        "1. Check if repository contains supported file types",
        "2. Verify file sizes are within processing limits",
        "3. Review file structure for parsing compatibility"
    ])
    
    # Create chunk
    fallback_chunk = {
        'id': 'review_fallback_summary',
        'type': 'review_fallback',
        'file_path': 'repository_summary',
        'language': 'text',
        'content': '\n'.join(content_lines),
        'metadata': {
            'chunk_type': 'review_fallback',
            'created_by': 'review_api_fallback',
            'total_files': len(files),
            'reason': 'empty_chunks_input'
        }
    }
    
    chunks.append(fallback_chunk)
    return chunks
