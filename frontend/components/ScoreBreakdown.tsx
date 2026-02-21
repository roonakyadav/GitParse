import { ScoreBreakdown as ScoreBreakdownType } from '../types';

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdownType;
}

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getBarColor = (score: number): string => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getBarWidth = (score: number): string => {
    return `w-[${Math.max(5, Math.min(100, score))}%]`;
  };

  const categories = [
    { key: 'code_quality', label: 'Code Quality', score: breakdown.code_quality },
    { key: 'security', label: 'Security', score: breakdown.security },
    { key: 'architecture', label: 'Architecture', score: breakdown.architecture },
    { key: 'skills', label: 'Skills', score: breakdown.skills }
  ];

  return (
    <div className="bg-[#1a1a1a] rounded-xl shadow-lg p-6 border border-[#2a2a2a]">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <svg className="w-5 h-5 mr-2 text-[#3b82f6]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Why This Score?
        </h3>
        <p className="text-sm text-[#b3b3b3] mt-1">
          Detailed breakdown of how your overall score was calculated
        </p>
      </div>

      <div className="space-y-4">
        {categories.map((category) => (
          <div key={category.key} className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-[#b3b3b3] font-medium">{category.label}</span>
              <span className={`font-semibold ${getScoreColor(category.score)}`}>
                {category.score.toFixed(1)}
              </span>
            </div>
            <div className="w-full bg-[#2a2a2a] rounded-full h-2">
              <div 
                className={`h-2 rounded-full ${getBarColor(category.score)} transition-all duration-500 ease-out`}
                style={{ width: `${Math.max(5, Math.min(100, category.score))}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-[#2a2a2a]">
        <div className="text-sm text-[#b3b3b3]">
          <p className="mb-1">Overall score calculation:</p>
          <p className="text-xs">• Code Quality: 30% weight</p>
          <p className="text-xs">• Security: 25% weight</p>
          <p className="text-xs">• Architecture: 25% weight</p>
          <p className="text-xs">• Skills: 20% weight</p>
        </div>
      </div>
    </div>
  );
}