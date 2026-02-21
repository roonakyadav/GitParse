'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { setCurrentRepoUrl } from '../lib/storage';

export default function HomePage() {
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const validateGithubUrl = (url: string): boolean => {
    const githubUrlPattern = /^https?:\/\/(www\.)?github\.com\/[^\/]+\/[^\/]+\/?$/;
    return githubUrlPattern.test(url);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL');
      return;
    }
    
    if (!validateGithubUrl(repoUrl)) {
      setError('Please enter a valid GitHub repository URL');
      return;
    }
    
    setIsLoading(true);
    
    try {
      console.log(`Starting new analysis for ${repoUrl}`);
      // Set the current repo URL to trigger data clearing
      setCurrentRepoUrl(repoUrl);
      // Store the URL in sessionStorage for the analyze page
      sessionStorage.setItem('repoUrl', repoUrl);
      router.push('/analyze');
    } catch (error) {
      setError('Failed to redirect to analysis page');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-[#1a1a1a] rounded-xl shadow-lg p-8 border border-[#2a2a2a]">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">RepoMind AI</h1>
          <p className="text-[#b3b3b3]">Analyze GitHub repositories with AI</p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="repoUrl" className="block text-sm font-medium text-[#b3b3b3] mb-2">
              GitHub Repository URL
            </label>
            <input
              type="url"
              id="repoUrl"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#3b82f6] focus:ring-offset-2 focus:ring-offset-[#0f0f0f] text-white"
              disabled={isLoading}
            />
          </div>
          
          {error && (
            <div className="text-red-400 text-sm py-2 px-3 bg-red-900/20 rounded-lg">{error}</div>
          )}
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-white text-[#0f0f0f] py-3 px-4 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-[#3b82f6] focus:ring-offset-2 focus:ring-offset-[#0f0f0f] disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {isLoading ? 'Analyzing...' : 'Analyze Repository'}
          </button>
        </form>
        
        <div className="mt-8 pt-6 border-t border-[#2a2a2a] text-center">
          <p className="text-[#b3b3b3] text-sm">Next Steps:</p>
          <div className="flex justify-center space-x-4 mt-2">
            <span className="text-[#3b82f6] font-medium">1. Home</span>
            <span className="text-[#b3b3b3]">→</span>
            <span className="text-[#b3b3b3]">2. Analyze</span>
            <span className="text-[#b3b3b3]">→</span>
            <span className="text-[#b3b3b3]">3. Process</span>
            <span className="text-[#b3b3b3]">→</span>
            <span className="text-[#b3b3b3]">4. Review</span>
          </div>
        </div>
      </div>
    </div>
  );
}
