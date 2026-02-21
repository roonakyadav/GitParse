import { useState, useEffect } from 'react';
import { ProgressStatus } from '../types';

interface ProgressTrackerProps {
  requestId: string;
  apiUrl: string;
  onCompleted?: () => void;
  onError?: (error: string) => void;
}

export function ProgressTracker({ requestId, apiUrl, onCompleted, onError }: ProgressTrackerProps) {
  const [progress, setProgress] = useState<ProgressStatus | null>(null);
  const [polling, setPolling] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!requestId || !polling) return;

    const fetchProgress = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/progress/${requestId}`);
        
        if (!response.ok) {
          if (response.status === 404) {
            // Progress not found, might be completed or expired
            setPolling(false);
            return;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: ProgressStatus = await response.json();
        setProgress(data);
        setError(null);

        // Check if completed
        if (data.completed) {
          setPolling(false);
          if (onCompleted) {
            onCompleted();
          }
        }

        // Check for errors
        if (data.error) {
          setPolling(false);
          setError(data.error);
          if (onError) {
            onError(data.error);
          }
        }

      } catch (err) {
        console.error('Failed to fetch progress:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch progress');
        // Continue polling despite errors (fail-safe)
      }
    };

    // Fetch immediately
    fetchProgress();

    // Set up polling interval
    const interval = setInterval(fetchProgress, 1000);

    // Cleanup
    return () => clearInterval(interval);
  }, [requestId, apiUrl, polling, onCompleted, onError]);

  const getStageStatus = (status: string) => {
    switch (status) {
      case 'done':
        return { symbol: '✔', className: 'text-green-400' };
      case 'running':
        return { symbol: '⏳', className: 'text-yellow-400' };
      case 'error':
        return { symbol: '❌', className: 'text-red-400' };
      case 'pending':
      default:
        return { symbol: '○', className: 'text-gray-500' };
    }
  };

  if (!requestId) {
    return null;
  }

  if (error && !progress) {
    return (
      <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
        <div className="text-center">
          <div className="text-red-400 mb-2">
            <svg className="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-white font-medium">Progress Tracking Error</p>
          <p className="text-gray-400 text-sm mt-1">{error}</p>
          <p className="text-gray-500 text-xs mt-2">
            Continuing analysis in background...
          </p>
        </div>
      </div>
    );
  }

  const stages = [
    { key: 'fetching', label: 'Fetching Repository' },
    { key: 'parsing', label: 'Parsing Files' },
    { key: 'chunking', label: 'Chunking Code' },
    { key: 'review', label: 'Running AI Review' }
  ];

  return (
    <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">Pipeline Status</h3>
        <p className="text-sm text-gray-400 mt-1">
          Real-time analysis progress
        </p>
      </div>

      <div className="space-y-3">
        {stages.map((stage) => {
          const status = progress ? progress[stage.key as keyof ProgressStatus] as string : 'pending';
          const { symbol, className } = getStageStatus(status);
          
          return (
            <div key={stage.key} className="flex items-center">
              <span className={`text-lg font-medium mr-3 ${className}`}>
                {symbol}
              </span>
              <span className={`text-white ${status === 'running' ? 'font-medium' : 'font-normal'}`}>
                {stage.label}
              </span>
              {status === 'running' && (
                <div className="ml-auto">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-400"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {progress?.error && (
        <div className="mt-4 p-3 bg-red-900/20 border border-red-800/50 rounded-lg">
          <p className="text-red-400 text-sm">
            Error: {progress.error}
          </p>
        </div>
      )}

      {progress?.completed && (
        <div className="mt-4 p-3 bg-green-900/20 border border-green-800/50 rounded-lg">
          <p className="text-green-400 text-sm">
            Analysis completed successfully!
          </p>
        </div>
      )}
    </div>
  );
}