export interface RepoFile {
  path: string;
  size: number;
  language: string;
  download_url: string;
}

export interface RepoAnalysis {
  repo: string;
  files: RepoFile[];
}

export interface ApiError {
  error: string;
}

export interface StoredRepoData {
  data: RepoAnalysis;
  timestamp: number;
}
