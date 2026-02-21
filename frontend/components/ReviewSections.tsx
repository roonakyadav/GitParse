'use client';

import { Severity, ReviewItem, SkillGap } from '../types';

interface SeverityBadgeProps {
  severity: Severity;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const getSeverityStyles = (severity: Severity): string => {
    switch (severity) {
      case 'high':
        return 'bg-red-900/30 text-red-400 border border-red-800/50';
      case 'medium':
        return 'bg-amber-900/30 text-amber-400 border border-amber-800/50';
      case 'low':
        return 'bg-emerald-900/30 text-emerald-400 border border-emerald-800/50';
      default:
        return 'bg-gray-900/30 text-gray-400 border border-gray-800/50';
    }
  };

  return (
    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full border ${getSeverityStyles(severity)}`}>
      {severity.toUpperCase()}
    </span>
  );
}

interface ReviewItemCardProps {
  item: ReviewItem;
  title: string;
  icon: React.ReactNode;
}

export function ReviewItemCard({ item, title, icon }: ReviewItemCardProps) {
  return (
    <div className="bg-[#1a1a1a] rounded-xl p-4 border border-[#2a2a2a] transition-all hover:border-[#3a3a3a]">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 text-[#b3b3b3]">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-white">{title}</h4>
            <SeverityBadge severity={item.severity} />
          </div>
          
          {/* File and lines information */}
          {(item.file || item.lines) && (
            <div className="mb-2 flex flex-wrap gap-2">
              {item.file && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-[#242424] text-[#b3b3b3] rounded-md">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> {item.file}
                </span>
              )}
              {item.lines && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-[#242424] text-[#b3b3b3] rounded-md">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Lines {item.lines}
                </span>
              )}
            </div>
          )}
          
          {/* Problem description */}
          <p className="text-sm text-[#b3b3b3] mb-2">
            {item.problem || item.description || 'No description available'}
          </p>
          
          {/* Code snippet */}
          {item.snippet && item.snippet !== 'Not available' && (
            <div className="mb-2 p-2 bg-[#242424] rounded-md border border-[#2a2a2a]">
              <p className="text-xs font-medium text-[#b3b3b3] mb-1">Code Evidence:</p>
              <pre className="text-xs text-[#f5f5f5] overflow-x-auto whitespace-pre-wrap font-mono">
                {item.snippet}
              </pre>
            </div>
          )}
          
          {/* Impact explanation */}
          {item.impact && item.impact !== 'Not available' && (
            <div className="mb-2 p-2 bg-amber-900/20 rounded-md border border-amber-800/50">
              <p className="text-sm text-amber-300">
                <span className="font-medium">Impact:</span> {item.impact}
              </p>
            </div>
          )}
          
          {/* Fix suggestion */}
          {(item.fix || item.suggestion) && (
            <div className="mt-2 p-2 bg-blue-900/20 rounded-md border border-blue-800/50">
              <p className="text-sm text-blue-300">
                <span className="font-medium">Fix:</span> {item.fix || item.suggestion}
              </p>
            </div>
          )}
          
          {/* Learning resource */}
          {item.resource && item.resource !== 'Not available' && (
            <div className="mt-2">
              <a
                href={item.resource}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#3b82f6] hover:text-[#60a5fa] underline"
              >
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg> Learn more →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface SkillGapCardProps {
  skillGap: SkillGap;
}

export function SkillGapCard({ skillGap }: SkillGapCardProps) {
  return (
    <div className="bg-[#1a1a1a] rounded-xl p-4 border border-[#2a2a2a] transition-all hover:border-[#3a3a3a]">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 text-[#b3b3b3]">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-white">{skillGap.skill}</h4>
            <SeverityBadge severity={skillGap.priority} />
          </div>
          
          {/* File and lines information */}
          {(skillGap.file || skillGap.lines) && (
            <div className="mb-2 flex flex-wrap gap-2">
              {skillGap.file && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-[#242424] text-[#b3b3b3] rounded-md">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg> {skillGap.file}
                </span>
              )}
              {skillGap.lines && (
                <span className="inline-flex items-center px-2 py-1 text-xs bg-[#242424] text-[#b3b3b3] rounded-md">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Lines {skillGap.lines}
                </span>
              )}
            </div>
          )}
          
          {/* Skill gap description */}
          <p className="text-sm text-[#b3b3b3] mb-2">
            {skillGap.gap || skillGap.description || 'No description available'}
          </p>
          
          {/* Code snippet */}
          {skillGap.snippet && skillGap.snippet !== 'Not available' && (
            <div className="mb-2 p-2 bg-[#242424] rounded-md border border-[#2a2a2a]">
              <p className="text-xs font-medium text-[#b3b3b3] mb-1">Code Example:</p>
              <pre className="text-xs text-[#f5f5f5] overflow-x-auto whitespace-pre-wrap font-mono">
                {skillGap.snippet}
              </pre>
            </div>
          )}
          
          {/* Impact explanation */}
          {skillGap.impact && skillGap.impact !== 'Not available' && (
            <div className="mb-2 p-2 bg-amber-900/20 rounded-md border border-amber-800/50">
              <p className="text-sm text-amber-300">
                <span className="font-medium">Why it matters:</span> {skillGap.impact}
              </p>
            </div>
          )}
          
          {/* Learning resources */}
          {(skillGap.resource || (skillGap.resources && skillGap.resources.length > 0)) && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-[#b3b3b3]">Learning Resources:</p>
              {skillGap.resource && skillGap.resource !== 'Not available' && (
                <a
                  href={skillGap.resource}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-[#3b82f6] hover:text-[#60a5fa] underline truncate"
                >
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg> {skillGap.resource}
                </a>
              )}
              {skillGap.resources && skillGap.resources.map((resource, index) => (
                <a
                  key={index}
                  href={resource}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-[#3b82f6] hover:text-[#60a5fa] underline truncate"
                >
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg> {resource}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface ReviewSectionProps {
  title: string;
  icon: React.ReactNode;
  items: ReviewItem[] | SkillGap[] | undefined;
  emptyMessage: string;
  renderItem: (item: ReviewItem | SkillGap, index: number) => React.ReactNode;
}

export function ReviewSection({ title, icon, items, emptyMessage, renderItem }: ReviewSectionProps) {
  const safeItems = Array.isArray(items) ? items : [];
  
  return (
    <div className="bg-[#1a1a1a] rounded-xl shadow-lg border border-[#2a2a2a]">
      <div className="px-6 py-4 border-b border-[#2a2a2a]">
        <div className="flex items-center space-x-2">
          <span className="text-[#b3b3b3]">{icon}</span>
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <span className="bg-[#2a2a2a] text-[#b3b3b3] text-xs px-2 py-1 rounded-full">
            {(safeItems ?? []).length}
          </span>
        </div>
      </div>
      
      <div className="p-6">
        {(safeItems ?? []).length === 0 ? (
          <div className="text-center py-8">
            <svg className="w-12 h-12 mx-auto text-[#b3b3b3]/50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            <p className="text-[#b3b3b3] mt-2">{emptyMessage}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {(safeItems ?? []).map((item, index) => renderItem(item, index))}
          </div>
        )}
      </div>
    </div>
  );
}
