import { useState } from 'react';

interface ProjectResumeSummaryProps {
  projectResume: string;
}

export function ProjectResumeSummary({ projectResume }: ProjectResumeSummaryProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(projectResume);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  if (!projectResume) {
    return null;
  }

  return (
    <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white flex items-center">
            <svg className="w-5 h-5 mr-2 text-[#3b82f6]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Project Resume Summary
          </h3>
          <p className="text-sm text-[#b3b3b3] mt-1">
            Professional summary for career building and resume inclusion
          </p>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center px-3 py-1.5 bg-[#2a2a2a] hover:bg-[#3a3a3a] text-[#b3b3b3] rounded-lg transition-colors text-sm"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          {copied ? 'Copied!' : 'Copy for Resume'}
        </button>
      </div>

      <div className="bg-[#2a2a2a] rounded-lg p-4">
        <p className="text-[#e5e5e5] leading-relaxed whitespace-pre-wrap">
          {projectResume}
        </p>
      </div>

      <div className="mt-4 flex items-center text-xs text-[#6b7280]">
        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        This summary is AI-generated based on technical analysis and suitable for professional use
      </div>
    </div>
  );
}