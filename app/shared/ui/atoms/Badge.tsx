/**
 * Badge Atom
 * 
 * ステータス表示用のバッジ。
 */

import { HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/cn';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-slate-700 text-slate-200',
        success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
        warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
        danger: 'bg-red-500/20 text-red-400 border border-red-500/30',
        info: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
        user: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
        assistant: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
        system: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

// Role バッジのヘルパー
export function RoleBadge({ role }: { role: 'USER' | 'ASSISTANT' | 'SYSTEM' }) {
  const variantMap = {
    USER: 'user',
    ASSISTANT: 'assistant',
    SYSTEM: 'system',
  } as const;
  
  return <Badge variant={variantMap[role]}>{role}</Badge>;
}
