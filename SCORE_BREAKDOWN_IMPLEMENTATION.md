# Score Breakdown Feature Implementation

## Overview
This document describes the implementation of the explainable "Score Breakdown" feature for RepoMind, which shows users exactly how the overall score is calculated.

## Feature Requirements
- Show transparent scoring breakdown for each component
- Display individual scores for: Code Quality, Security, Architecture, Skills
- Calculate overall score as weighted average
- Provide clear visualization in the review page
- Work with both AI analysis and fallback modes

## Implementation Details

### Backend Changes

#### 1. Schema Updates (`schemas.py`)
Added `ScoreBreakdown` model:
```python
class ScoreBreakdown(BaseModel):
    code_quality: float
    security: float
    architecture: float
    skills: float
```

#### 2. AI Reviewer Logic (`ai/reviewer.py`)
Added two new methods:

**`_calculate_component_score(items, component_type)`**
- Calculates individual component scores (0-100)
- Higher score when fewer issues found
- Deducts points based on issue severity:
  - High severity: -15 points each
  - Medium severity: -8 points each
  - Low severity: -3 points each
- Base score: 95 (high baseline for good code)

**`_calculate_overall_score(code_quality, security, architecture, skills)`**
- Computes weighted average:
  - Code Quality: 30% weight
  - Security: 25% weight
  - Architecture: 25% weight
  - Skills: 20% weight

#### 3. API Response Updates (`main.py`)
- Ensures `score_breakdown` field is always present
- Provides fallback breakdown when missing
- Added logging for transparency

### Frontend Changes

#### 1. Type Definitions (`types/index.ts`)
Added `ScoreBreakdown` interface:
```typescript
export interface ScoreBreakdown {
  code_quality: number;
  security: number;
  architecture: number;
  skills: number;
}
```

#### 2. New Component (`components/ScoreBreakdown.tsx`)
Created dedicated UI component with:
- Professional dark theme styling
- Visual progress bars for each component
- Color-coded scores (green/yellow/red)
- Weight information display
- Responsive design

#### 3. Review Page Integration (`app/review/page.tsx`)
- Added ScoreBreakdown component below Overall Score card
- Conditional rendering when breakdown data exists
- Maintains existing UI structure

## Scoring Logic

### Component Score Calculation
```
Base Score: 95.0
Deductions:
- High severity issues: -15 each
- Medium severity issues: -8 each
- Low severity issues: -3 each

Final Score = max(0, min(100, Base Score - Total Deductions))
```

### Overall Score Calculation
```
Overall Score = (Code Quality × 0.30) + 
                (Security × 0.25) + 
                (Architecture × 0.25) + 
                (Skills × 0.20)
```

## Example Output

### Backend Response
```json
{
  "success": true,
  "score": 83.1,
  "score_breakdown": {
    "code_quality": 82.5,
    "security": 90.0,
    "architecture": 75.5,
    "skills": 85.0
  },
  "issues": [...],
  "security": [...],
  "architecture": [...],
  "skills": [...]
}
```

### Frontend Display
```
Why This Score?
─────────────────
Code Quality    ████████ 82.5
Security        █████████ 90.0
Architecture    ███████ 75.5
Skills          ████████ 85.0

Overall score calculation:
• Code Quality: 30% weight
• Security: 25% weight
• Architecture: 25% weight
• Skills: 20% weight
```

## Validation & Testing

### Backend Validation
- Component score calculation accuracy
- Overall score weighted average computation
- Score breakdown structure validation
- Fallback analysis score handling
- Range validation (0-100)

### Test Results
✅ All validation tests passed:
- Individual component scores calculated correctly
- Overall score computed as weighted average
- Score breakdown structure is valid
- All scores are within 0-100 range

## Logging & Transparency

### Backend Logging
```
INFO: Score breakdown: {'code_quality': 82.5, 'security': 90.0, 'architecture': 75.5, 'skills': 85.0}
INFO: Overall score: 83.1
```

### Fallback Logging
```
INFO: Fallback analysis created with score 75.0
INFO: Score breakdown: {'code_quality': 75.0, 'security': 75.0, 'architecture': 75.0, 'skills': 75.0}
```

## Error Handling

### Graceful Degradation
- If score breakdown missing, creates fallback with 75.0 for all components
- Maintains backward compatibility with existing API responses
- Safe handling of missing or invalid data

### Validation
- Ensures all scores are numeric and within valid range
- Validates required fields exist in breakdown
- Handles edge cases (empty issue lists, etc.)

## Performance Impact
- Minimal overhead: simple arithmetic calculations
- No additional API calls or external dependencies
- Client-side rendering of visualization components
- Efficient data structure for score transmission

## Future Enhancements
- Configurable weight percentages
- Detailed breakdown of issue scoring
- Historical score comparison
- Export functionality for score reports
- Custom scoring rules per project type

## Files Modified
1. `/backend/schemas.py` - Added ScoreBreakdown model
2. `/backend/ai/reviewer.py` - Added score calculation logic
3. `/backend/main.py` - Ensured breakdown in API response
4. `/frontend/types/index.ts` - Added ScoreBreakdown interface
5. `/frontend/components/ScoreBreakdown.tsx` - New UI component
6. `/frontend/app/review/page.tsx` - Integrated breakdown display
7. `/backend/test_score_breakdown.py` - Validation tests

## Deployment Notes
- No database schema changes required
- Backward compatible with existing frontend
- No breaking API changes
- Can be deployed incrementally