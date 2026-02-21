from pydantic import BaseModel
from typing import List, Optional


class RepoFile(BaseModel):
    path: str
    size: int
    language: str
    download_url: str


class RepoAnalysis(BaseModel):
    repo: str
    files: List[RepoFile]
    light_mode: Optional[bool] = False
    analysis_mode: Optional[str] = "full"
    limited: Optional[bool] = False
    reason: Optional[str] = None
    retry_after: Optional[str] = None
    
    class Config:
        # Allow additional fields to be set dynamically
        extra = "allow"


class AnalyzeRequest(BaseModel):
    repo_url: str


class ApiError(BaseModel):
    error: str
