'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { RepoAnalysis, RepoFile } from '../../types';
import { saveRepoData, loadRepoData, getCurrentRepoUrl, clearRepoData } from '../../lib/storage';
import { API_URL } from '../../lib/config';

export default function AnalyzePage() {
  const [repoData, setRepoData] = useState<RepoAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    analyzeRepository();
  }, []);

  const analyzeRepository = async () => {
    try {
      // Get URL from sessionStorage
      const repoUrl = sessionStorage.getItem('repoUrl');
      if (!repoUrl) {
        setError('No repository URL provided');
        setIsLoading(false);
        return;
      }

      console.log(`Analyzing repository: ${repoUrl}`);
      
      // Always call backend API for fresh analysis
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to analyze repository');
      }

      const data: RepoAnalysis = await response.json();
      setRepoData(data);
      // Save minimal repo info for tracking purposes
      saveRepoData(data);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getLanguageColor = (language: string): string => {
    const colors: { [key: string]: string } = {
      python: 'bg-blue-900/30 text-blue-400 border border-blue-800/50',
      javascript: 'bg-yellow-900/30 text-yellow-400 border border-yellow-800/50',
      typescript: 'bg-blue-900/30 text-blue-400 border border-blue-800/50',
      java: 'bg-red-900/30 text-red-400 border border-red-800/50',
      cpp: 'bg-purple-900/30 text-purple-400 border border-purple-800/50',
      c: 'bg-gray-900/30 text-gray-400 border border-gray-800/50',
      go: 'bg-cyan-900/30 text-cyan-400 border border-cyan-800/50',
      rust: 'bg-orange-900/30 text-orange-400 border border-orange-800/50',
      html: 'bg-pink-900/30 text-pink-400 border border-pink-800/50',
      css: 'bg-indigo-900/30 text-indigo-400 border border-indigo-800/50',
      json: 'bg-green-900/30 text-green-400 border border-green-800/50',
      markdown: 'bg-gray-900/30 text-gray-400 border border-gray-800/50',
      text: 'bg-gray-900/30 text-gray-400 border border-gray-800/50',
    };
    return colors[language] || 'bg-gray-900/30 text-gray-400 border border-gray-800/50';
  };

  const handleBack = () => {
    router.push('/');
  };

  const handleNewAnalysis = () => {
    console.log('Starting new analysis from analyze page');
    // Clear all stored data and go back to home
    clearRepoData();
    router.push('/');
  };

  const handleNext = () => {
    router.push('/process');
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setError('');
    analyzeRepository();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3b82f6] mx-auto mb-4"></div>
          <p className="text-[#b3b3b3]">Analyzing repository...</p>
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
            <h2 className="text-xl font-semibold text-white mb-2">Analysis Failed</h2>
            <p className="text-[#b3b3b3] mb-6">{error}</p>
            <div className="space-x-4">
              <button
                onClick={handleRefresh}
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

  if (!repoData) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#b3b3b3]">No repository data available</p>
          <button
            onClick={handleBack}
            className="mt-4 bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <div className="bg-[#1a1a1a] shadow-sm border-b border-[#2a2a2a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-white">Repository Analysis</h1>
              <p className="text-[#b3b3b3]">{repoData.repo}</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleRefresh}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Refresh
              </button>
              <button
                onClick={handleNewAnalysis}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                New Analysis
              </button>
              <button
                onClick={handleNext}
                className="bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium"
              >
                Next: Process
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-[#1a1a1a] rounded-xl shadow-lg overflow-hidden border border-[#2a2a2a]">
          <div className="px-6 py-4 border-b border-[#2a2a2a]">
            <h2 className="text-lg font-semibold text-white">
              Files ({repoData.files.length})
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[#2a2a2a]">
              <thead className="bg-[#242424]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#b3b3b3] uppercase tracking-wider">
                    Path
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#b3b3b3] uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[#b3b3b3] uppercase tracking-wider">
                    Language
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2a2a]">
                {repoData.files.map((file: RepoFile, index: number) => (
                  <tr key={index} className="hover:bg-[#242424] transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                      {file.path}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-[#b3b3b3]">
                      {formatFileSize(file.size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-3 py-1 text-xs font-medium rounded-md ${getLanguageColor(file.language)}`}>
                        {file.language}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
