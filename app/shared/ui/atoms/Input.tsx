/**
 * Input Atom
 * 
 * テキスト入力フィールド。
 */

import { forwardRef, InputHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, type = 'text', ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-lg border bg-slate-900 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500',
          'transition-colors duration-200',
          'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950',
          error
            ? 'border-red-500 focus:ring-red-500'
            : 'border-slate-700 focus:border-cyan-500 focus:ring-cyan-500',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';
