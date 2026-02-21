// API Configuration
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Storage Configuration
export const STORAGE_KEY = 'repomind_repo_data';
export const STORAGE_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

// UI Configuration
export const MAX_FILE_SIZE_DISPLAY = 500 * 1024; // 500KB for display purposes
