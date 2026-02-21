import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from schemas import AnalyzeRequest, RepoAnalysis, ApiError
from github import parse_repo_url, process_repo_files
from processing.indexer import create_repository_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RepoMind AI API", 
    version="2.0.0",
    description="GitHub repository analysis API with Phase 2 processing"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
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
        files = await process_repo_files(owner, repo)
        
        result = RepoAnalysis(
            repo=f"{owner}/{repo}",
            files=files
        )
        
        logger.info(f"Analysis completed: {len(files)} files found")
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
        
        logger.info(f"Phase 2 processing completed: {index['total_files']} files, {index['total_chunks']} chunks")
        return index
    
    except Exception as e:
        logger.error(f"Phase 2 processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RepoMind AI API is running", 
        "version": "2.0.0",
        "phase": "Phase 2 - Code Processing Engine"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "phase": "Phase 2"
    }
