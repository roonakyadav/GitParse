from pydantic import BaseModel
from typing import List, Optional


class RepoFile(BaseModel):
    path: str
    size: int
    language: str
    download_url: str


class ScoreBreakdown(BaseModel):
    code_quality: float
    security: float
    architecture: float
    skills: float
    
    class Config:
        # Allow additional fields to be set dynamically
        extra = "allow"


class RepoAnalysis(BaseModel):
    repo: str
    files: List[RepoFile]
    light_mode: Optional[bool] = False
    analysis_mode: Optional[str] = "full"
    limited: Optional[bool] = False
    reason: Optional[str] = None
    retry_after: Optional[str] = None
    safe_mode: Optional[bool] = False
    
    class Config:
        # Allow additional fields to be set dynamically
        extra = "allow"


class AnalyzeRequest(BaseModel):
    repo_url: str


class ApiError(BaseModel):
    error: str


class ProjectResume(BaseModel):
    project_resume: str
    
    class Config:
        # Allow additional fields to be set dynamically
        extra = "allow"


class ProgressStatus(BaseModel):
    request_id: str
    fetching: str  # pending|running|done|error
    parsing: str   # pending|running|done|error
    chunking: str  # pending|running|done|error
    review: str    # pending|running|done|error
    error: Optional[str] = None
    completed: bool = False
    
    class Config:
        # Allow additional fields to be set dynamically
        extra = "allow"
