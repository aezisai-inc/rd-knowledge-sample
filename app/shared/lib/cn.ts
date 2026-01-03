/**
 * Class Name Utility
 * 
 * Tailwind CSS クラス名を安全にマージ。
 * clsx + tailwind-merge のラッパー。
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
