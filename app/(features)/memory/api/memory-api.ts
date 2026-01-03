/**
 * Memory Feature API
 *
 * FSD features/memory/api 層
 * GraphQL API とのインターフェース
 */

import { getGraphQLClient, executeQuery } from '../../../shared/api/graphql-client';

// Types
export interface MemorySession {
  sessionId: string;
  startTime: string;
  endTime?: string | null;
  title?: string | null;
  tags?: string[] | null;
}

export interface MemoryEvent {
  id: string;
  actorId: string;
  sessionId: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown> | null;
}

/**
 * Create a new memory session
 */
export async function createMemorySession(
  title?: string,
  tags?: string[]
): Promise<MemorySession> {
  const client = getGraphQLClient();

  const result = await client.mutations.createMemorySession({
    title,
    tags,
  });

  if (!result.data) {
    throw new Error('Failed to create memory session');
  }

  return result.data as MemorySession;
}

/**
 * Get memory session by ID
 */
export async function getMemorySession(sessionId: string): Promise<MemorySession | null> {
  const client = getGraphQLClient();

  const result = await client.queries.getMemorySession({
    sessionId,
  });

  return (result.data as MemorySession) || null;
}

/**
 * Get memory events for a session
 */
export async function getMemoryEvents(
  actorId: string,
  sessionId?: string,
  limit?: number
): Promise<MemoryEvent[]> {
  const client = getGraphQLClient();

  const result = await client.queries.getMemoryEvents({
    actorId,
    sessionId,
    limit,
  });

  return (result.data as MemoryEvent[]) || [];
}

/**
 * Create a new memory event
 */
export async function createMemoryEvent(
  actorId: string,
  sessionId: string,
  role: 'USER' | 'ASSISTANT' | 'SYSTEM',
  content: string,
  metadata?: Record<string, unknown>
): Promise<MemoryEvent> {
  const client = getGraphQLClient();

  const result = await client.mutations.createMemoryEvent({
    actorId,
    sessionId,
    role,
    content,
    metadata,
  });

  if (!result.data) {
    throw new Error('Failed to create memory event');
  }

  return result.data as MemoryEvent;
}

/**
 * Delete a memory session
 */
export async function deleteMemorySession(sessionId: string): Promise<boolean> {
  const client = getGraphQLClient();

  const result = await client.mutations.deleteMemorySession({
    sessionId,
  });

  return result.data === true;
}
