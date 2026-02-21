import { RepoAnalysis, StoredRepoData } from '../types';
import { STORAGE_KEY, STORAGE_EXPIRY_MS } from './config';

export function saveRepoData(data: RepoAnalysis): void {
  try {
    if (typeof window === 'undefined') return; // SSR safety
    
    const storedData: StoredRepoData = {
      data,
      timestamp: Date.now()
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(storedData));
  } catch (error) {
    console.warn('Failed to save repo data to localStorage:', error);
  }
}

export function loadRepoData(): RepoAnalysis | null {
  try {
    if (typeof window === 'undefined') return null; // SSR safety
    
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    
    const storedData: StoredRepoData = JSON.parse(stored);
    
    // Check if data is expired
    if (Date.now() - storedData.timestamp > STORAGE_EXPIRY_MS) {
      clearRepoData();
      return null;
    }
    
    return storedData.data;
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
