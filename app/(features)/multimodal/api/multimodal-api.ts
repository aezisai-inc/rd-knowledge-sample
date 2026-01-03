/**
 * Multimodal Feature API
 *
 * FSD features/multimodal/api 層
 * Nova Pro/Lite + Canvas + Reel との GraphQL インターフェース
 */

import { getGraphQLClient } from '../../../shared/api/graphql-client';

// Types
export interface ImageOutput {
  base64?: string | null;
  seed?: number | null;
}

export interface VideoOutput {
  url?: string | null;
}

export interface MultimodalResponse {
  message?: string | null;
  images?: ImageOutput[] | null;
  videos?: VideoOutput[] | null;
  metadata?: Record<string, unknown> | null;
}

export interface MultimodalRequest {
  sessionId: string;
  prompt: string;
  image?: string; // Base64 encoded
}

/**
 * Invoke multimodal agent
 *
 * @param request - Multimodal request with prompt and optional image
 * @returns Response with message, images, and/or videos
 */
export async function invokeMultimodal(
  request: MultimodalRequest
): Promise<MultimodalResponse> {
  const client = getGraphQLClient();

  const result = await client.mutations.invokeMultimodal({
    sessionId: request.sessionId,
    prompt: request.prompt,
    image: request.image,
  });

  if (!result.data) {
    throw new Error('Failed to invoke multimodal agent');
  }

  return result.data as MultimodalResponse;
}

/**
 * Generate image using Nova Canvas
 */
export async function generateImage(
  sessionId: string,
  prompt: string
): Promise<ImageOutput[]> {
  const response = await invokeMultimodal({
    sessionId,
    prompt: `画像を生成: ${prompt}`,
  });

  return response.images || [];
}

/**
 * Generate video using Nova Reel
 */
export async function generateVideo(
  sessionId: string,
  prompt: string
): Promise<VideoOutput[]> {
  const response = await invokeMultimodal({
    sessionId,
    prompt: `動画を生成: ${prompt}`,
  });

  return response.videos || [];
}

/**
 * Analyze image using Nova Vision
 */
export async function analyzeImage(
  sessionId: string,
  imageBase64: string,
  prompt: string
): Promise<string> {
  const response = await invokeMultimodal({
    sessionId,
    prompt,
    image: imageBase64,
  });

  return response.message || '';
}
