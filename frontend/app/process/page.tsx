'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { loadRepoData, saveRepoData } from '../../lib/storage';
import { API_URL } from '../../lib/config';

interface ProcessedData {
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
      // Load Phase 1 data from localStorage
      const phase1Data = loadRepoData();
      if (!phase1Data) {
        setError('No repository data found. Please analyze a repository first.');
        setIsLoading(false);
        return;
      }

      // Call Phase 2 processing API
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
      setProcessedData(data);
      
      // Save processed data
      saveRepoData({ ...phase1Data, processed: data });
      
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
    const { chunks_within_limits, total_chunks } = processedData.processing_stats;
    return total_chunks > 0 ? (chunks_within_limits / total_chunks) * 100 : 0;
  };

  const handleBack = () => {
    router.push('/analyze');
  };

  const handleNewAnalysis = () => {
    router.push('/');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Processing repository...</p>
          <p className="text-sm text-gray-500 mt-2">Analyzing code structure and dependencies</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
          <div className="text-center">
            <div className="text-red-600 mb-4">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Processing Failed</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="space-x-4">
              <button
                onClick={processRepository}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleBack}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors"
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No processing data available</p>
          <button
            onClick={handleBack}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            Back to Analysis
          </button>
        </div>
      </div>
    );
  }

  const tokenEfficiency = getTokenEfficiency();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Repository Processing</h1>
              <p className="text-gray-600">{processedData.repo}</p>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={processRepository}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Re-process
              </button>
              <button
                onClick={handleBack}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors"
              >
                Back to Analysis
              </button>
              <button
                onClick={handleNewAnalysis}
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
              >
                New Analysis
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Files</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(processedData.total_files)}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Chunks</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(processedData.total_chunks)}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Tokens</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(processedData.total_tokens)}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Processing Time</div>
            <div className="text-2xl font-bold text-gray-900">{formatTime(processedData.processing_stats.processing_time_seconds)}</div>
          </div>
        </div>

        {/* Token Statistics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Token Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Average tokens per chunk:</span>
                <span className="font-medium">{processedData.avg_tokens.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Min tokens:</span>
                <span className="font-medium">{processedData.min_tokens}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Max tokens:</span>
                <span className="font-medium">{processedData.max_tokens}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Chunks within limits (300-800):</span>
                <span className="font-medium">{tokenEfficiency.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Results</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Files processed:</span>
                <span className="font-medium text-green-600">{processedData.processing_stats.files_processed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Files failed:</span>
                <span className="font-medium text-red-600">{processedData.processing_stats.files_failed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Chunks created:</span>
                <span className="font-medium">{processedData.processing_stats.chunks_created}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Chunks too large:</span>
                <span className="font-medium text-orange-600">{processedData.processing_stats.chunks_too_large}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Languages */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Languages</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {Object.entries(processedData.languages).map(([lang, count]) => (
              <div key={lang} className="text-center">
                <div className="text-lg font-medium text-gray-900">{lang}</div>
                <div className="text-sm text-gray-500">{count} files</div>
              </div>
            ))}
          </div>
        </div>

        {/* Dependencies */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Dependencies</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm font-medium text-gray-500 mb-2">Total Dependencies</div>
              <div className="text-xl font-bold text-gray-900">{formatNumber(processedData.dependencies.total_dependencies)}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500 mb-2">Circular Dependencies</div>
              <div className="text-xl font-bold text-red-600">{processedData.dependencies.graph.circular_dependencies.length}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500 mb-2">Top-level Files</div>
              <div className="text-xl font-bold text-green-600">{processedData.dependencies.graph.top_level_files.length}</div>
            </div>
          </div>
          
          {processedData.dependencies.graph.circular_dependencies.length > 0 && (
            <div className="mt-4 p-4 bg-red-50 rounded-md">
              <div className="text-sm text-red-800">
                <strong>Warning:</strong> {processedData.dependencies.graph.circular_dependencies.length} circular dependencies detected.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
