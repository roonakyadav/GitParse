export interface RepoFile {
  path: string;
  size: number;
  language: string;
  download_url: string;
}

export interface RepoAnalysis {
  repo: string;
  files: RepoFile[];
  processed?: ProcessedData;
}

export interface ProcessedData {
  success?: boolean;
  error?: string;
  repo: string;
  total_files: number;
  total_chunks: number;
  total_tokens: number;
  max_tokens: number;
  min_tokens: number;
  avg_tokens: number;
  languages: Record<string, number>;
  file_types: Record<string, number>;
  processing_stats: {
    processing_time_seconds: number;
    files_processed: number;
    files_failed: number;
    chunks_created: number;
    chunks_within_limits: number;
    chunks_too_large: number;
    chunks_too_small: number;
  };
  dependencies: {
    total_dependencies: number;
    graph: {
      circular_dependencies: any[];
      top_level_files: string[];
      leaf_files: string[];
    };
  };
}

export interface ApiError {
  error: string;
}

export interface StoredRepoData {
  data: RepoAnalysis;
  timestamp: number;
}

// AI Review Types
export type Severity = 'high' | 'medium' | 'low';

export interface ReviewItem {
  file?: string;
  description: string;
  severity: Severity;
  suggestion?: string;
  resource?: string;
}

export interface SkillGap {
  skill: string;
  description: string;
  priority: Severity;
  resources: string[];
}

export interface AIReviewResponse {
  success: boolean;
  repo?: string;
  score: number;  // Changed from overall_score to match backend
  issues: ReviewItem[];  // Changed from code_quality_issues to match backend
  security: ReviewItem[];  // Changed from security_warnings to match backend
  architecture: ReviewItem[];  // Changed from architecture_feedback to match backend
  skills: SkillGap[];  // Changed from skill_gaps to match backend
  summary?: string;
  error?: string;
  chunks_analyzed?: number;
  total_chunks?: number;
  failed_reviews?: number;
  fallback_analysis?: boolean;
}

// Keep backward compatibility aliases
export interface AIReviewResponseLegacy {
  success: boolean;
  repo?: string;
  overall_score: number;
  code_quality_issues: ReviewItem[];
  security_warnings: ReviewItem[];
  architecture_feedback: ReviewItem[];
  skill_gaps: SkillGap[];
  summary?: string;
  error?: string;
  chunks_analyzed?: number;
  total_chunks?: number;
  failed_reviews?: number;
}

export interface StoredReviewData {
  data: AIReviewResponse;
  timestamp: number;
}
