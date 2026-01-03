'use client';

import React, { useState, useCallback } from 'react';
import { cn } from '../../../shared/lib/cn';
import { Button } from '../../../shared/ui/atoms/Button';
import { Textarea } from '../../../shared/ui/atoms/Textarea';
import { Spinner } from '../../../shared/ui/atoms/Spinner';
import { ImagePreview } from '../../../shared/ui/molecules/ImagePreview';
import { ChatMessage } from '../../../shared/ui/molecules/ChatMessage';
import {
  invokeMultimodal,
  type MultimodalResponse,
  type ImageOutput,
} from '../api/multimodal-api';

type TabId = 'chat' | 'image' | 'video';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  images?: ImageOutput[];
}

export function MultimodalPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('chat');
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentPrompt = prompt;
    setPrompt('');
    setIsLoading(true);

    try {
      const response = await invokeMultimodal({
        sessionId,
        prompt: currentPrompt,
      });

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.message || 'Response received',
        timestamp: new Date().toISOString(),
        images: response.images?.filter(
          (img): img is { base64: string; seed?: number } => !!img.base64
        ),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Multimodal request failed:', error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [prompt, sessionId, isLoading]);

  const tabs: { id: TabId; label: string }[] = [
    { id: 'chat', label: 'Chat' },
    { id: 'image', label: 'Image Generation' },
    { id: 'video', label: 'Video Generation' },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Tab navigation */}
      <div className="flex border-b border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id}>
            <ChatMessage
              role={message.role}
              content={message.content}
              timestamp={message.timestamp}
            />
            {message.images && message.images.length > 0 && (
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 max-w-[80%] ml-auto">
                {message.images.map((image, idx) => (
                  <ImagePreview
                    key={idx}
                    src={image.base64 || ''}
                    seed={image.seed || undefined}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400">
            <Spinner size="sm" />
            <span className="text-sm">Processing with Nova...</span>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              activeTab === 'image'
                ? 'Describe the image to generate...'
                : activeTab === 'video'
                ? 'Describe the video to generate...'
                : 'Send a message to Nova Pro...'
            }
            disabled={isLoading}
            className="flex-1 min-h-[60px] max-h-[120px]"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <Button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isLoading}
            className="self-end"
          >
            {isLoading ? <Spinner size="sm" /> : 'Send'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          {activeTab === 'image'
            ? 'Nova Canvas will generate images based on your description'
            : activeTab === 'video'
            ? 'Nova Reel will generate videos (async processing)'
            : 'Nova Pro/Lite for multimodal understanding'}
        </p>
      </div>
    </div>
  );
}
