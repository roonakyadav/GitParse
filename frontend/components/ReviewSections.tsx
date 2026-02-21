'use client';

import { Severity, ReviewItem, SkillGap } from '../types';

interface SeverityBadgeProps {
  severity: Severity;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const getSeverityStyles = (severity: Severity): string => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 text-gray-400">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-900">{title}</h4>
            <SeverityBadge severity={item.severity} />
          </div>
          
          {item.file && (
            <div className="mb-2">
              <span className="inline-flex items-center px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-md">
                📁 {item.file}
              </span>
            </div>
          )}
          
          <p className="text-sm text-gray-700 mb-2">{item.description || 'No description available'}</p>
          
          {item.suggestion && (
            <div className="mt-2 p-2 bg-blue-50 rounded-md">
              <p className="text-sm text-blue-800">
                <span className="font-medium">💡 Suggestion:</span> {item.suggestion}
              </p>
            </div>
          )}
          
          {item.resource && (
            <div className="mt-2">
              <a
                href={item.resource}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                📚 Learn more →
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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 text-gray-400">
          🎯
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-900">{skillGap.skill}</h4>
            <SeverityBadge severity={skillGap.priority} />
          </div>
          
          <p className="text-sm text-gray-700 mb-3">{skillGap.description || 'No description available'}</p>
          
          {skillGap.resources && skillGap.resources.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-gray-500">Resources:</p>
              {skillGap.resources.map((resource, index) => (
                <a
                  key={index}
                  href={resource}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-blue-600 hover:text-blue-800 underline truncate"
                >
                  📚 {resource}
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
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <span className="text-gray-400">{icon}</span>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">
            {(safeItems ?? []).length}
          </span>
        </div>
      </div>
      
      <div className="p-6">
        {(safeItems ?? []).length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 text-4xl mb-2">📋</div>
            <p className="text-gray-500">{emptyMessage}</p>
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
