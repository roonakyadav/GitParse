'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AIReviewResponse, ReviewItem, SkillGap } from '../../types';
import { loadRepoData, clearRepoData } from '../../lib/storage';
import { API_URL } from '../../lib/config';
import { 
  ReviewSection, 
  ReviewItemCard, 
  SkillGapCard, 
  SeverityBadge 
} from '../../components/ReviewSections';
import { ErrorBoundary } from '../../components/ErrorBoundary';

export default function ReviewPageWrapper() {
  return (
    <ErrorBoundary>
      <ReviewPage />
    </ErrorBoundary>
  );
}

function ReviewPage() {
  const [reviewData, setReviewData] = useState<AIReviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    performAIReview();
  }, []);

  const performAIReview = async () => {
    try {
      // Load processed repo data from localStorage
      const storedData = loadRepoData();
      if (!storedData) {
        setError('No repository data found. Please analyze and process a repository first.');
        setIsLoading(false);
        return;
      }

      // Check if we have processed data (Phase 2)
      if (!storedData.processed) {
        setError('Repository processing data not found. Please complete the processing step first.');
        setIsLoading(false);
        return;
      }

      console.log(`Performing AI review for repository: ${storedData.repo}`);
      
      // Always call Phase 3 AI Review API for fresh analysis
      const response = await fetch(`${API_URL}/api/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(storedData.processed),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || errorData.error || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMessage);
      }

      const data: AIReviewResponse = await response.json();
      
      // Validate API response structure
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response format from server');
      }
      
      // Check if API returned success: false
      if (!data.success) {
        throw new Error(data.error || 'AI analysis failed');
      }
      
      // Validate score is a valid number
      if (data.score === undefined || data.score === null || isNaN(Number(data.score))) {
        throw new Error('Invalid score received from AI analysis');
      }
      
      // Normalize response data to prevent undefined arrays
      const normalizedData: AIReviewResponse = {
        ...data,
        issues: data.issues || [],
        security: data.security || [],
        architecture: data.architecture || [],
        skills: data.skills || [],
        score: Number(data.score) // Ensure score is a number
      };
      
      setReviewData(normalizedData);
      
    } catch (error) {
      console.error('AI Review error:', error);
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          setError('Unable to connect to the backend. Please ensure the backend is running on http://localhost:8000');
        } else if (error.message.includes('CORS')) {
          setError('CORS error: Please check backend configuration');
        } else {
          setError(error.message);
        }
      } else {
        setError('An unexpected error occurred during AI review');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getScoreBackground = (score: number): string => {
    if (score >= 80) return 'bg-emerald-900/20 border-emerald-800/50';
    if (score >= 60) return 'bg-amber-900/20 border-amber-800/50';
    return 'bg-red-900/20 border-red-800/50';
  };

  const handleBack = () => {
    router.push('/process');
  };

  const handleNewAnalysis = () => {
    console.log('Starting new analysis from review page');
    // Clear all stored data and go back to home
    clearRepoData();
    router.push('/');
  };

  const handleRetry = () => {
    setIsLoading(true);
    setError('');
    performAIReview();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3b82f6] mx-auto mb-4"></div>
          <p className="text-[#b3b3b3]">Performing AI Review...</p>
          <p className="text-sm text-[#6b7280] mt-2">Analyzing code quality, security, and architecture</p>
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
            <h2 className="text-xl font-semibold text-white mb-2">AI Review Failed</h2>
            <p className="text-[#b3b3b3] mb-6">{error}</p>
            <div className="space-x-4">
              <button
                onClick={handleRetry}
                className="bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleBack}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Back to Processing
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!reviewData) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#b3b3b3]">No review data available</p>
          <button
            onClick={handleBack}
            className="mt-4 bg-white text-[#0f0f0f] px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Back to Processing
          </button>
        </div>
      </div>
    );
  }

  // Check if all sections are empty
  const allSectionsEmpty = 
    (!reviewData.issues || reviewData.issues.length === 0) &&
    (!reviewData.security || reviewData.security.length === 0) &&
    (!reviewData.architecture || reviewData.architecture.length === 0) &&
    (!reviewData.skills || reviewData.skills.length === 0);

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      {/* Header */}
      <div className="bg-[#1a1a1a] shadow-sm border-b border-[#2a2a2a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-white">AI Review</h1>
              <p className="text-[#b3b3b3]">{reviewData.repo || 'Repository'}</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleRetry}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Re-run Review
              </button>
              <button
                onClick={handleBack}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                Back to Processing
              </button>
              <button
                onClick={handleNewAnalysis}
                className="bg-[#2a2a2a] text-[#b3b3b3] px-4 py-2 rounded-lg hover:bg-[#3a3a3a] transition-colors"
              >
                New Analysis
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Overall Score Card */}
        <div className={`bg-[#1a1a1a] rounded-xl shadow-lg p-8 border-2 ${getScoreBackground(reviewData.score)}`}>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-white mb-4">📊 Overall Score</h2>
            <div className={`text-6xl font-bold mb-4 ${getScoreColor(reviewData.score)}`}>
              {reviewData.score}/100
            </div>
            <div className="max-w-2xl mx-auto">
              <p className="text-[#b3b3b3]">
                {reviewData.summary || `Analysis completed with score ${reviewData.score}/100`}
              </p>
              {reviewData.failed_reviews && reviewData.failed_reviews > 0 && (
                <p className="text-sm text-amber-400 mt-2">
                  Note: {reviewData.failed_reviews} analysis type(s) failed to complete
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Code Quality Issues */}
        <ReviewSection
          title="⚠️ Code Quality Issues"
          icon="⚠️"
          items={reviewData.issues}
          emptyMessage="No code quality issues found! Great job!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Code Quality Issue"
              icon="⚠️"
            />
          )}
        />

        {/* Security Warnings */}
        <ReviewSection
          title="🔐 Security Warnings"
          icon="🔐"
          items={reviewData.security}
          emptyMessage="No security vulnerabilities detected!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Security Warning"
              icon="🔐"
            />
          )}
        />

        {/* Architecture Feedback */}
        <ReviewSection
          title="🏗️ Architecture Feedback"
          icon="🏗️"
          items={reviewData.architecture}
          emptyMessage="No architecture concerns identified!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Architecture Feedback"
              icon="🏗️"
            />
          )}
        />

        {/* Skill Gaps */}
        <ReviewSection
          title="🎯 Skill Gaps & Learning Resources"
          icon="🎯"
          items={reviewData.skills}
          emptyMessage="No specific skill gaps identified!"
          renderItem={(item, index) => (
            <SkillGapCard
              key={index}
              skillGap={item as SkillGap}
            />
          )}
        />

        {/* Show message if all sections are empty */}
        {allSectionsEmpty && (
          <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-8 border border-[#2a2a2a]">
            <div className="text-center">
              <div className="text-emerald-400 text-4xl mb-4">✅</div>
              <h3 className="text-lg font-semibold text-white mb-2">No major issues found</h3>
              <p className="text-[#b3b3b3]">
                Great job! Your codebase appears to be in good condition with no significant issues detected.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
