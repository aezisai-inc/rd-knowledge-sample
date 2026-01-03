'use client';

import React from 'react';
import { cn } from '../../lib/cn';

interface ImagePreviewProps {
  src: string;
  alt?: string;
  seed?: number;
  className?: string;
  onDownload?: () => void;
}

export function ImagePreview({
  src,
  alt = 'Generated image',
  seed,
  className,
  onDownload,
}: ImagePreviewProps) {
  const imageUrl = src.startsWith('data:') ? src : `data:image/png;base64,${src}`;

  const handleDownload = () => {
    if (onDownload) {
      onDownload();
    } else {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.download = `generated-${seed || Date.now()}.png`;
      link.click();
    }
  };

  return (
    <div className={cn('relative group', className)}>
      <img
        src={imageUrl}
        alt={alt}
        className="w-full h-auto rounded-lg border border-gray-700"
      />
      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
        <button
          onClick={handleDownload}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium text-white transition-colors"
        >
          Download
        </button>
      </div>
      {seed !== undefined && (
        <div className="absolute bottom-2 right-2 px-2 py-1 bg-black/70 rounded text-xs text-gray-400">
          Seed: {seed}
        </div>
      )}
    </div>
  );
}
