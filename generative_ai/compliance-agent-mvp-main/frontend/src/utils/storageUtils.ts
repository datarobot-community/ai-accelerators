/**
 * Storage utilities for managing custom columns in localStorage
 */
import { type CustomColumn } from '../types/compliance';

const STORAGE_KEY = 'compliance_custom_columns';

/**
 * Save custom columns to localStorage
 */
export function saveCustomColumns(columns: CustomColumn[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(columns));
  } catch (error) {
    console.error('Failed to save custom columns to localStorage:', error);
  }
}

/**
 * Load custom columns from localStorage
 * Returns null if no columns are saved
 */
export function loadCustomColumns(): CustomColumn[] | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return null;
    }
    const parsed = JSON.parse(stored);
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return null;
  } catch (error) {
    console.error('Failed to load custom columns from localStorage:', error);
    return null;
  }
}

/**
 * Clear saved custom columns from localStorage
 */
export function clearCustomColumns(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear custom columns from localStorage:', error);
  }
}

/**
 * Check if user has saved custom columns
 */
export function hasCustomColumns(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== null;
  } catch {
    return false;
  }
}

// ============================================
// Custom Prompts Storage
// ============================================

const PROMPTS_STORAGE_KEY = 'compliance_custom_prompts';

export interface StoredPrompts {
  systemPrompt: string;
}

/**
 * Save custom prompts to localStorage
 */
export function saveCustomPrompts(prompts: StoredPrompts): void {
  try {
    localStorage.setItem(PROMPTS_STORAGE_KEY, JSON.stringify(prompts));
  } catch (error) {
    console.error('Failed to save custom prompts to localStorage:', error);
  }
}

/**
 * Load custom prompts from localStorage
 * Returns null if no prompts are saved
 */
export function loadCustomPrompts(): StoredPrompts | null {
  try {
    const stored = localStorage.getItem(PROMPTS_STORAGE_KEY);
    if (!stored) {
      return null;
    }
    const parsed = JSON.parse(stored);
    if (parsed && typeof parsed.systemPrompt === 'string') {
      return parsed as StoredPrompts;
    }
    return null;
  } catch (error) {
    console.error('Failed to load custom prompts from localStorage:', error);
    return null;
  }
}

/**
 * Clear saved custom prompts from localStorage
 */
export function clearCustomPrompts(): void {
  try {
    localStorage.removeItem(PROMPTS_STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear custom prompts from localStorage:', error);
  }
}

/**
 * Check if user has saved custom prompts
 */
export function hasCustomPrompts(): boolean {
  try {
    return localStorage.getItem(PROMPTS_STORAGE_KEY) !== null;
  } catch {
    return false;
  }
}

