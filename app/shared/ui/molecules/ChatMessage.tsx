'use client';

import React from 'react';
import { cn } from '../../lib/cn';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  className?: string;
}

const roleStyles = {
  user: 'bg-blue-600/20 border-blue-600/30 ml-auto',
  assistant: 'bg-green-600/20 border-green-600/30 mr-auto',
  system: 'bg-gray-600/20 border-gray-600/30 mx-auto text-center',
};

const roleLabels = {
  user: 'You',
  assistant: 'AI Assistant',
  system: 'System',
};

export function ChatMessage({ role, content, timestamp, className }: ChatMessageProps) {
  return (
    <div
      className={cn(
        'max-w-[80%] rounded-lg border p-4',
        roleStyles[role],
        className
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-400">{roleLabels[role]}</span>
        {timestamp && (
          <span className="text-xs text-gray-500">
            {new Date(timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>
      <p className="text-sm text-white whitespace-pre-wrap">{content}</p>
    </div>
  );
}
