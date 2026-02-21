'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loadRepoData, saveRepoData, clearRepoData } from '../../lib/storage';
import { API_URL } from '../../lib/config';
import { ProcessedData } from '../../types';

export default function ProcessPage() {
  const [processedData, setProcessedData] = useState<ProcessedData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    processRepository();
  }, []);

  const processRepository = async () => {
    try {
      // Load Phase 1 data - may return null if localStorage overflow protection triggered
      let phase1Data = loadRepoData();
      
      // If no data in localStorage (due to minimal storage), fetch fresh data from backend
      if (!phase1Data) {
        const repoUrl = sessionStorage.getItem('repoUrl');
        if (!repoUrl) {
          setError('No repository URL provided. Please analyze a repository first.');
          setIsLoading(false);
          return;
        }

        // Fetch fresh Phase 1 data from backend API
        const analyzeResponse = await fetch(`${API_URL}/api/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ repo_url: repoUrl }),
        });

        if (!analyzeResponse.ok) {
          const errorData = await analyzeResponse.json();
          throw new Error(errorData.detail || 'Failed to fetch repository data');
        }

        phase1Data = await analyzeResponse.json();
      }
      
      // Check if phase1Data is null
      if (!phase1Data) {
        setError('No repository data found. Please analyze a repository first.');
        setIsLoading(false);
        return;
      }
      
      console.log(`Processing repository: ${phase1Data.repo}`);
      
      // Always call Phase 2 processing API for fresh processing
      const response = await fetch(`${API_URL}/api/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(phase1Data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process repository');
      }

      const data: ProcessedData = await response.json();
      
      // Check if API returned success: false
      if (data.success === false) {
        throw new Error(data.error || 'Repository processing failed');
      }
      
      setProcessedData(data);
      
      // Save minimal repo info for tracking purposes
      if (phase1Data && phase1Data.repo) {
        saveRepoData({ ...phase1Data, processed: data });
      }
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    return `${(seconds / 60).toFixed(1)}m`;
  };

  const getTokenEfficiency = (): number => {
    if (!processedData) return 0;
    const { chunks_within_limits, chunks_created } = processedData.processing_stats;
    return chunks_created > 0 ? (chunks_within_limits / chunks_created) * 100 : 0;
  };

  const handleBack = () => {
    router.push('/analyze');
  };

  const handleNewAnalysis = () => {
    console.log('Starting new analysis from process page');
    // Clear all stored data and go back to home
    clearRepoData();
    router.push('/');
  };

  const handleRunAIReview = () => {
    router.push('/review');
  };

  const handleNext = () => {
    router.push('/review');
  };

  // Check if chunks are available for AI review
  const hasChunks = processedData && processedData.total_chunks > 0;
  const chunksWarning = !hasChunks ? "No chunks available - AI review may fail" : "";

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3b82f6] mx-auto mb-4"></div>
          <p className="text-[#b3b3b3]">Processing repository...</p>
          <p className="text-sm text-[#6b7280] mt-2">Analyzing code structure and dependencies</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-[#1a1a1a] rounded-xl shadow-lg p-8 border border-[#2a2a2a]">
          <div className="text-center">
            <div className="text-red-400 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">Processing Failed</h2>
            <p className="text-[#b3b3b3] mb-6">{error}</p>
            <div className="space-x-4">
              <button
                onClick={processRepository}
                className="bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleBack}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Back
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!processedData) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#b3b3b3]">No processing data available</p>
          <button
            onClick={handleBack}
            className="mt-4 bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Back to Analysis
          </button>
        </div>
      </div>
    );
  }

  const tokenEfficiency = getTokenEfficiency();

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <div className="bg-[#1a1a1a] shadow-sm border-b border-[#2a2a2a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-white">Repository Processing</h1>
              <p className="text-[#b3b3b3]">{processedData.repo}</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleRunAIReview}
                disabled={!hasChunks}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  !hasChunks 
                    ? 'bg-[#4b5563] text-[#9ca3af] cursor-not-allowed' 
                    : 'bg-[#3b82f6] text-white hover:bg-[#2563eb]'
                }`}
                title={chunksWarning}
              >
                Run AI Review
              </button>
              <button
                onClick={processRepository}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Re-process
              </button>
              <button
                onClick={handleBack}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Back to Analysis
              </button>
              <button
                onClick={handleNext}
                className="bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                Next: Review
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Warning when no chunks */}
        {!hasChunks && (
          <div className="bg-amber-900/20 border border-amber-800/50 rounded-xl p-6 mb-8">
            <div className="flex items-start space-x-3">
              <div className="text-amber-500">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-medium text-amber-400 mb-2">No Chunks Available</h3>
                <p className="text-amber-300 mb-3">
                  No code chunks were generated during processing. This may happen when:
                </p>
                <ul className="list-disc list-inside text-amber-300 space-y-1">
                  <li>Repository contains only binary files</li>
                  <li>Files are too large or too small for processing</li>
                  <li>Unsupported file types</li>
                  <li>Parsing errors occurred</li>
                </ul>
                <p className="text-amber-300 mt-3">
                  <strong>Recommendation:</strong> Try re-processing the repository or analyze a different repository with source code files.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <div className="text-sm font-medium text-[#b3b3b3]">Total Files</div>
            <div className="text-2xl font-bold text-white">{formatNumber(processedData.total_files)}</div>
          </div>
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <div className="text-sm font-medium text-[#b3b3b3]">Total Chunks</div>
            <div className="text-2xl font-bold text-white">{formatNumber(processedData.total_chunks)}</div>
          </div>
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <div className="text-sm font-medium text-[#b3b3b3]">Total Tokens</div>
            <div className="text-2xl font-bold text-white">{formatNumber(processedData.total_tokens)}</div>
          </div>
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <div className="text-sm font-medium text-[#b3b3b3]">Processing Time</div>
            <div className="text-2xl font-bold text-white">{formatTime(processedData.processing_stats.processing_time_seconds)}</div>
          </div>
        </div>

        {/* Token Statistics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <h3 className="text-lg font-semibold text-white mb-4">Token Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Average tokens per chunk:</span>
                <span className="font-medium text-white">{processedData.avg_tokens.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Min tokens:</span>
                <span className="font-medium text-white">{processedData.min_tokens}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Max tokens:</span>
                <span className="font-medium text-white">{processedData.max_tokens}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Chunks within limits (300-800):</span>
                <span className="font-medium text-white">{tokenEfficiency.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
            <h3 className="text-lg font-semibold text-white mb-4">Processing Results</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Files processed:</span>
                <span className="font-medium text-emerald-400">{processedData.processing_stats.files_processed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Files failed:</span>
                <span className="font-medium text-red-400">{processedData.processing_stats.files_failed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Chunks created:</span>
                <span className="font-medium text-white">{processedData.processing_stats.chunks_created}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#b3b3b3]">Chunks too large:</span>
                <span className="font-medium text-amber-400">{processedData.processing_stats.chunks_too_large}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Languages */}
        <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 mb-8 border border-[#2a2a2a]">
          <h3 className="text-lg font-semibold text-white mb-4">Languages</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {Object.entries(processedData.languages).map(([lang, count]) => (
              <div key={lang} className="text-center">
                <div className="text-lg font-medium text-white">{lang}</div>
                <div className="text-sm text-[#b3b3b3]">{count} files</div>
              </div>
            ))}
          </div>
        </div>

        {/* Dependencies */}
        <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
          <h3 className="text-lg font-semibold text-white mb-4">Dependencies</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm font-medium text-[#b3b3b3] mb-2">Total Dependencies</div>
              <div className="text-xl font-bold text-white">{formatNumber(processedData.dependencies.total_dependencies)}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-[#b3b3b3] mb-2">Circular Dependencies</div>
              <div className="text-xl font-bold text-red-400">{processedData.dependencies.graph.circular_dependencies.length}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-[#b3b3b3] mb-2">Top-level Files</div>
              <div className="text-xl font-bold text-emerald-400">{processedData.dependencies.graph.top_level_files.length}</div>
            </div>
          </div>
          
          {processedData.dependencies.graph.circular_dependencies.length > 0 && (
            <div className="mt-4 p-4 bg-red-900/20 rounded-lg border border-red-800/50">
              <div className="text-sm text-red-300">
                <strong>Warning:</strong> {processedData.dependencies.graph.circular_dependencies.length} circular dependencies detected.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
