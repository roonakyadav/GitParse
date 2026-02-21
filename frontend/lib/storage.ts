import { RepoAnalysis, StoredRepoData } from '../types';
import { STORAGE_KEY, STORAGE_EXPIRY_MS } from './config';

// Minimal repository info to store in localStorage
interface MinimalRepoInfo {
  repoUrl: string;
  analysisId?: string;
  timestamp: number;
}

// Track the current repository URL to detect when a new repo is entered
let currentRepoUrl: string | null = null;

export function setCurrentRepoUrl(url: string): void {
  currentRepoUrl = url;
  // Clear any existing data when setting a new repo URL
  clearRepoData();
}

export function getCurrentRepoUrl(): string | null {
  return currentRepoUrl;
}

export function saveRepoData(data: RepoAnalysis): void {
  try {
    if (typeof window === 'undefined') return; // SSR safety
    
    // Create minimal storage data to avoid localStorage overflow
    const minimalData: MinimalRepoInfo = {
      repoUrl: data.repo,
      analysisId: generateAnalysisId(data),
      timestamp: Date.now()
    };
    
    // Try to save minimal data to localStorage
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(minimalData));
    } catch (storageError) {
      console.warn('localStorage quota exceeded, skipping storage:', storageError);
      // Still allow the operation to continue, but without localStorage persistence
    }
  } catch (error) {
    console.warn('Failed to prepare repo data for storage:', error);
  }
}

// Helper function to generate a compact identifier for the analysis
function generateAnalysisId(data: RepoAnalysis): string {
  // Create a simple hash-like identifier based on repo name and timestamp
  const baseString = `${data.repo}-${data.files.length}`;
  let hash = 0;
  for (let i = 0; i < baseString.length; i++) {
    const char = baseString.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(32);
}

export function loadRepoData(): RepoAnalysis | null {
  try {
    if (typeof window === 'undefined') return null; // SSR safety
    
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    
    // Parse minimal data from localStorage
    const storedData: MinimalRepoInfo = JSON.parse(stored);
    
    // Check if data is expired
    if (Date.now() - storedData.timestamp > STORAGE_EXPIRY_MS) {
      clearRepoData();
      return null;
    }
    
    // Since we only store minimal info, return null to indicate that
    // the full data needs to be fetched from the backend
    return null;
  } catch (error) {
    console.warn('Error loading repo data:', error);
    return null;
  }
}

export function clearRepoData(): void {
  try {
    if (typeof window === 'undefined') return; // SSR safety
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to clear repo data:', error);
  }
}
