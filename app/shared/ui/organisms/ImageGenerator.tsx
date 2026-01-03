'use client';

import React, { useState } from 'react';
import { cn } from '../../lib/cn';
import { Button } from '../atoms/Button';
import { Textarea } from '../atoms/Textarea';
import { Spinner } from '../atoms/Spinner';
import { ImagePreview } from '../molecules/ImagePreview';

interface GeneratedImage {
  base64: string;
  seed?: number;
}

interface ImageGeneratorProps {
  onGenerate: (prompt: string) => Promise<GeneratedImage[]>;
  className?: string;
}

export function ImageGenerator({ onGenerate, className }: ImageGeneratorProps) {
  const [prompt, setPrompt] = useState('');
  const [images, setImages] = useState<GeneratedImage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await onGenerate(prompt);
      setImages(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Input area */}
      <div className="space-y-2">
        <Textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the image you want to generate..."
          disabled={isLoading}
          className="min-h-[100px]"
        />
        <Button
          onClick={handleGenerate}
          disabled={!prompt.trim() || isLoading}
          className="w-full"
        >
          {isLoading ? (
            <>
              <Spinner size="sm" className="mr-2" />
              Generating...
            </>
          ) : (
            'Generate Image'
          )}
        </Button>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/20 border border-red-500/30 text-red-400">
          {error}
        </div>
      )}

      {/* Generated images */}
      {images.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {images.map((image, index) => (
            <ImagePreview
              key={index}
              src={image.base64}
              seed={image.seed}
              alt={`Generated image ${index + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
