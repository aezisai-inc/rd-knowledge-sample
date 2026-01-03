'use client';

import React, { useState, useCallback } from 'react';
import { ChatInterface } from '../../../shared/ui/organisms/ChatInterface';
import { Button } from '../../../shared/ui/atoms/Button';
import {
  createMemorySession,
  createMemoryEvent,
  getMemoryEvents,
  type MemoryEvent,
} from '../api/memory-api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export function MemoryChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const startNewSession = useCallback(async () => {
    setIsLoading(true);
    try {
      const session = await createMemorySession('Test Session', ['test', 'demo']);
      setSessionId(session.sessionId);
      setMessages([
        {
          id: `system-${Date.now()}`,
          role: 'system',
          content: `New session started: ${session.sessionId}`,
          timestamp: session.startTime,
        },
      ]);
    } catch (error) {
      console.error('Failed to start session:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) return;

      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Create user event in memory
        await createMemoryEvent('user', sessionId, 'USER', content);

        // Simulate assistant response (in real app, this would call the agent)
        const assistantContent = `Received: "${content}". This message has been stored in AgentCore Memory.`;

        // Create assistant event in memory
        await createMemoryEvent('assistant', sessionId, 'ASSISTANT', assistantContent);

        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: assistantContent,
          timestamp: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        console.error('Failed to send message:', error);
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

  const loadHistory = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      const events = await getMemoryEvents('user', sessionId);
      const loadedMessages: Message[] = events.map((event: MemoryEvent) => ({
        id: event.id,
        role: event.role.toLowerCase() as 'user' | 'assistant' | 'system',
        content: event.content,
        timestamp: event.timestamp,
      }));
      setMessages(loadedMessages);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  return (
    <div className="h-full flex flex-col">
      {/* Session controls */}
      <div className="p-4 border-b border-gray-700 flex items-center gap-4">
        <Button onClick={startNewSession} disabled={isLoading}>
          New Session
        </Button>
        {sessionId && (
          <>
            <Button onClick={loadHistory} disabled={isLoading} variant="outline">
              Load History
            </Button>
            <span className="text-sm text-gray-400">
              Session: {sessionId.slice(0, 20)}...
            </span>
          </>
        )}
      </div>

      {/* Chat interface */}
      {sessionId ? (
        <ChatInterface
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          placeholder="Test AgentCore Memory..."
          className="flex-1"
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <p>Click "New Session" to start testing AgentCore Memory</p>
        </div>
      )}
    </div>
  );
}
