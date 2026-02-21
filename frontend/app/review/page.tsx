'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AIReviewResponse, ReviewItem, SkillGap } from '../../types';
import { loadRepoData } from '../../lib/storage';
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

      // Call Phase 3 AI Review API
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
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBackground = (score: number): string => {
    if (score >= 80) return 'bg-green-50 border-green-200';
    if (score >= 60) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  };

  const handleBack = () => {
    router.push('/process');
  };

  const handleNewAnalysis = () => {
    router.push('/');
  };

  const handleRetry = () => {
    setIsLoading(true);
    setError('');
    performAIReview();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Performing AI Review...</p>
          <p className="text-sm text-gray-500 mt-2">Analyzing code quality, security, and architecture</p>
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
            <h2 className="text-xl font-semibold text-gray-900 mb-2">AI Review Failed</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <div className="space-x-4">
              <button
                onClick={handleRetry}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={handleBack}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors"
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No review data available</p>
          <button
            onClick={handleBack}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI Review</h1>
              <p className="text-gray-600">{reviewData.repo || 'Repository'}</p>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={handleRetry}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                Re-run Review
              </button>
              <button
                onClick={handleBack}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 transition-colors"
              >
                Back to Processing
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

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Overall Score Card */}
        <div className={`bg-white rounded-lg shadow-sm border-2 p-8 ${getScoreBackground(reviewData.score)}`}>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">📊 Overall Score</h2>
            <div className={`text-6xl font-bold mb-4 ${getScoreColor(reviewData.score)}`}>
              {reviewData.score}/100
            </div>
            <div className="max-w-2xl mx-auto">
              <p className="text-gray-700">
                {reviewData.summary || `Analysis completed with score ${reviewData.score}/100`}
              </p>
              {reviewData.failed_reviews && reviewData.failed_reviews > 0 && (
                <p className="text-sm text-yellow-600 mt-2">
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
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <div className="text-center">
              <div className="text-green-600 text-4xl mb-4">✅</div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No major issues found</h3>
              <p className="text-gray-600">
                Great job! Your codebase appears to be in good condition with no significant issues detected.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
