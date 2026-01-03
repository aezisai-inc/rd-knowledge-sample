/**
 * Voice Feature API
 *
 * FSD features/voice/api 層
 * Nova Sonic との GraphQL インターフェース
 */

import { getGraphQLClient } from '../../../shared/api/graphql-client';

// Types
export interface VoiceResponse {
  transcript?: string | null;
  userText?: string | null;
  assistantText?: string | null;
  audio?: string | null; // Base64 encoded
  metadata?: Record<string, unknown> | null;
}

export interface VoiceRequest {
  sessionId: string;
  text: string;
}

/**
 * Send text to voice agent
 *
 * @param request - Voice request with session ID and text
 * @returns Response with assistant text and optional audio
 */
export async function sendVoiceText(request: VoiceRequest): Promise<VoiceResponse> {
  const client = getGraphQLClient();

  const result = await client.mutations.sendVoiceText({
    sessionId: request.sessionId,
    text: request.text,
  });

  if (!result.data) {
    throw new Error('Failed to send voice text');
  }

  return result.data as VoiceResponse;
}

/**
 * Start a voice conversation
 */
export async function startVoiceConversation(
  sessionId: string,
  initialMessage: string
): Promise<VoiceResponse> {
  return sendVoiceText({
    sessionId,
    text: initialMessage,
  });
}

/**
 * Continue voice conversation
 */
export async function continueConversation(
  sessionId: string,
  message: string
): Promise<VoiceResponse> {
  return sendVoiceText({
    sessionId,
    text: message,
  });
}

/**
 * Play audio response (browser utility)
 */
export function playAudioResponse(base64Audio: string): Promise<void> {
  return new Promise((resolve, reject) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
      audio.onended = () => resolve();
      audio.onerror = (e) => reject(e);
      audio.play();
    } catch (error) {
      reject(error);
    }
  });
}
