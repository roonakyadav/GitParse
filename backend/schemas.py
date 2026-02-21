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


class AnalyzeRequest(BaseModel):
    repo_url: str


class ApiError(BaseModel):
    error: str
