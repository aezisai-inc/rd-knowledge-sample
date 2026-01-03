'use client';

import React, { useState, useCallback } from 'react';
import { ChatInterface } from '../../../shared/ui/organisms/ChatInterface';
import { Button } from '../../../shared/ui/atoms/Button';
import { sendVoiceText, playAudioResponse } from '../api/voice-api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  audio?: string;
}

export function VoicePanel() {
  const [sessionId] = useState(() => `voice-${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [playingId, setPlayingId] = useState<string | null>(null);

  const handleSendMessage = useCallback(
    async (content: string) => {
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const response = await sendVoiceText({
          sessionId,
          text: content,
        });

        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.assistantText || 'No response',
          timestamp: new Date().toISOString(),
          audio: response.audio || undefined,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Voice request failed:', error);
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const handlePlayAudio = useCallback(async (messageId: string, audio: string) => {
    try {
      setPlayingId(messageId);
      await playAudioResponse(audio);
    } catch (error) {
      console.error('Failed to play audio:', error);
    } finally {
      setPlayingId(null);
    }
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white">Voice Dialogue</h2>
        <p className="text-sm text-gray-400">
          Powered by Nova Sonic - Text-to-Speech AI
        </p>
      </div>

      {/* Chat area with custom message rendering */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            <p>Start a voice conversation...</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-[80%] rounded-lg border p-4 ${
                message.role === 'user'
                  ? 'bg-blue-600/20 border-blue-600/30 ml-auto'
                  : message.role === 'assistant'
                  ? 'bg-green-600/20 border-green-600/30 mr-auto'
                  : 'bg-gray-600/20 border-gray-600/30 mx-auto text-center'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-400">
                  {message.role === 'user'
                    ? 'You'
                    : message.role === 'assistant'
                    ? 'AI Assistant'
                    : 'System'}
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-sm text-white whitespace-pre-wrap">{message.content}</p>
              {message.audio && (
                <div className="mt-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handlePlayAudio(message.id, message.audio!)}
                    disabled={playingId === message.id}
                  >
                    {playingId === message.id ? '▶ Playing...' : '🔊 Play Audio'}
                  </Button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-700 p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const input = (e.target as HTMLFormElement).elements.namedItem(
              'message'
            ) as HTMLInputElement;
            if (input.value.trim()) {
              handleSendMessage(input.value.trim());
              input.value = '';
            }
          }}
          className="flex gap-2"
        >
          <input
            name="message"
            type="text"
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 rounded-md border border-gray-700 bg-gray-800/50 px-3 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Sending...' : 'Send'}
          </Button>
        </form>
      </div>
    </div>
  );
}
