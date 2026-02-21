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
import { ScoreBreakdown } from '../../components/ScoreBreakdown';
import { ProjectResumeSummary } from '../../components/ProjectResumeSummary';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import { ProgressTracker } from '../../components/ProgressTracker';

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
      // Load processed repo data - may return null if localStorage overflow protection triggered
      let storedData = loadRepoData();
      
      // If no data in localStorage (due to minimal storage), fetch fresh data from backend
      if (!storedData) {
        const repoUrl = sessionStorage.getItem('repoUrl');
        if (!repoUrl) {
          setError('No repository URL provided. Please analyze and process a repository first.');
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

        const phase1Data = await analyzeResponse.json();

        // Fetch fresh processed data from backend API
        const processResponse = await fetch(`${API_URL}/api/process`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(phase1Data),
        });

        if (!processResponse.ok) {
          const errorData = await processResponse.json();
          throw new Error(errorData.detail || 'Failed to fetch processed repository data');
        }

        storedData = { ...phase1Data, processed: await processResponse.json() };
      }

      // Check if storedData is null or if we have processed data (Phase 2)
      if (!storedData || !storedData.processed) {
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

      {/* Progress Tracker */}
      {reviewData.request_id && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <ProgressTracker 
            requestId={reviewData.request_id}
            apiUrl={API_URL}
          />
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Overall Score Card */}
        <div className={`bg-[#1a1a1a] rounded-xl shadow-lg p-8 border-2 ${getScoreBackground(reviewData.score)}`}>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-white mb-4">Overall Score</h2>
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

        {/* Score Breakdown */}
        {reviewData.score_breakdown && (
          <ScoreBreakdown breakdown={reviewData.score_breakdown} />
        )}

        {/* Project Resume Summary */}
        {reviewData.project_resume && (
          <ProjectResumeSummary projectResume={reviewData.project_resume} />
        )}

        {/* Code Quality Issues */}
        <ReviewSection
          title="Code Quality Issues"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>}
          items={reviewData.issues}
          emptyMessage="No code quality issues found! Great job!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Code Quality Issue"
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>}
            />
          )}
        />

        {/* Security Warnings */}
        <ReviewSection
          title="Security Warnings"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>}
          items={reviewData.security}
          emptyMessage="No security vulnerabilities detected!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Security Warning"
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>}
            />
          )}
        />

        {/* Architecture Feedback */}
        <ReviewSection
          title="Architecture Feedback"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>}
          items={reviewData.architecture}
          emptyMessage="No architecture concerns identified!"
          renderItem={(item, index) => (
            <ReviewItemCard
              key={index}
              item={item as ReviewItem}
              title="Architecture Feedback"
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>}
            />
          )}
        />

        {/* Skill Gaps */}
        <ReviewSection
          title="Skill Gaps & Learning Resources"
          icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>}
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
              <svg className="w-12 h-12 mx-auto text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
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
