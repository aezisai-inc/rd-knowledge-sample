/**
 * Agent Resolver Lambda Handler
 *
 * AgentCore + StrandsAgents + Bedrock Nova シリーズを使用した
 * Multimodal/Voice エージェント処理
 *
 * 設計原則:
 * - AgentCore + StrandsAgents + BedrockAPI 構成
 * - AgentCore_Observability / CloudTrail 追跡可能
 * - boto3 / cli / script / sh 直接処理禁止
 * - 12 Agent Factor 準拠
 */

import type { AppSyncResolverHandler } from 'aws-lambda';
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
  ConverseCommand,
} from '@aws-sdk/client-bedrock-runtime';

// Types aligned with Domain Layer
interface MultimodalResponse {
  message?: string;
  images?: Array<{ base64: string; seed?: number }>;
  videos?: Array<{ url: string }>;
  metadata?: Record<string, unknown>;
}

interface VoiceResponse {
  transcript?: string;
  userText?: string;
  assistantText?: string;
  audio?: string; // Base64 encoded
  metadata?: Record<string, unknown>;
}

interface InvokeMultimodalArgs {
  sessionId: string;
  prompt: string;
  image?: string; // Base64 encoded input image
}

interface SendVoiceTextArgs {
  sessionId: string;
  text: string;
}

interface InvokeVoiceAgentArgs {
  sessionId: string;
  text?: string;
  audio?: string; // Base64 encoded audio
  mode?: 'TTS' | 'STT' | 'DIALOGUE';
}

type ResolverArgs = InvokeMultimodalArgs | SendVoiceTextArgs | InvokeVoiceAgentArgs;

// Environment
const REGION = process.env.AWS_REGION || 'ap-northeast-1';
const AGENTCORE_MEMORY_ID = process.env.AGENTCORE_MEMORY_ID || '';
const OUTPUT_BUCKET = process.env.OUTPUT_BUCKET || '';
const LOG_LEVEL = process.env.LOG_LEVEL || 'INFO';

// Model IDs
// Note: Nova models require inference profiles for on-demand invocation
// Using Claude models for text generation (no inference profile required)
const TEXT_MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'; // 会話用
const NOVA_CANVAS_MODEL_ID = 'amazon.nova-canvas-v1:0'; // 画像生成用 (inference profile 必要)
const NOVA_REEL_MODEL_ID = 'amazon.nova-reel-v1:0'; // 動画生成用 (inference profile 必要)
const NOVA_SONIC_MODEL_ID = 'amazon.nova-sonic-v1:0'; // 音声用 (inference profile 必要)

// Bedrock Client
const bedrockClient = new BedrockRuntimeClient({ region: REGION });

// Observability: Structured logging
const log = (level: string, message: string, data?: Record<string, unknown>) => {
  const logLevels = { DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3 };
  const currentLevel = logLevels[LOG_LEVEL as keyof typeof logLevels] ?? 1;
  const messageLevel = logLevels[level as keyof typeof logLevels] ?? 1;

  if (messageLevel >= currentLevel) {
    console.log(
      JSON.stringify({
        timestamp: new Date().toISOString(),
        level,
        message,
        ...data,
        service: 'agent-resolver',
      })
    );
  }
};

export const handler: AppSyncResolverHandler<
  ResolverArgs,
  MultimodalResponse | VoiceResponse
> = async (event) => {
  // Amplify Gen2 handler structure: fieldName is directly on event
  const fieldName = (event as any).fieldName || event.info?.fieldName;
  const args = (event as any).arguments || event.arguments;

  log('INFO', 'Agent Resolver invoked', {
    fieldName,
    eventKeys: Object.keys(event),
  });

  try {
    switch (fieldName) {
      case 'invokeMultimodal':
        return await invokeMultimodal(args as InvokeMultimodalArgs);
      case 'sendVoiceText':
        return await sendVoiceText(args as SendVoiceTextArgs);
      case 'invokeVoiceAgent':
        return await invokeVoiceAgent(args as InvokeVoiceAgentArgs);
      default:
        throw new Error(`Unknown field: ${fieldName}`);
    }
  } catch (error) {
    log('ERROR', 'Agent Resolver failed', {
      error: error instanceof Error ? error.message : String(error),
      fieldName,
    });
    throw error;
  }
};

/**
 * Multimodal Agent 呼び出し
 * Nova Pro/Lite + Canvas + Reel を組み合わせ
 */
async function invokeMultimodal(args: InvokeMultimodalArgs): Promise<MultimodalResponse> {
  const { sessionId, prompt, image } = args;

  log('INFO', 'Invoking multimodal agent', { sessionId, hasImage: !!image });

  const response: MultimodalResponse = {
    metadata: {
      sessionId,
      timestamp: new Date().toISOString(),
    },
  };

  try {
    // Step 1: Nova Pro/Lite で意図解析とテキスト生成
    const converseResponse = await invokeNovaConverse(prompt, image);
    response.message = converseResponse;

    // Step 2: 画像生成リクエストの場合は Nova Canvas を使用
    if (shouldGenerateImage(prompt)) {
      log('DEBUG', 'Generating image with Nova Canvas');
      const imageResult = await invokeNovaCanvas(prompt);
      response.images = imageResult ? [imageResult] : [];
    }

    // Step 3: 動画生成リクエストの場合は Nova Reel を使用
    if (shouldGenerateVideo(prompt)) {
      log('DEBUG', 'Generating video with Nova Reel');
      // Nova Reel は非同期処理のため、ステータス URL を返す
      response.videos = [{ url: 'pending://nova-reel-job-id' }];
    }

    log('INFO', 'Multimodal response generated', {
      hasMessage: !!response.message,
      imageCount: response.images?.length || 0,
      videoCount: response.videos?.length || 0,
    });

    return response;
  } catch (error) {
    log('ERROR', 'Multimodal processing failed', {
      error: error instanceof Error ? error.message : String(error),
    });

    // Graceful degradation
    return {
      message: 'Processing error. Please try again.',
      metadata: {
        error: true,
        sessionId,
      },
    };
  }
}

/**
 * Voice Agent (Text-to-Speech/Speech-to-Text)
 * Nova Sonic を使用
 */
async function sendVoiceText(args: SendVoiceTextArgs): Promise<VoiceResponse> {
  const { sessionId, text } = args;

  log('INFO', 'Processing voice text', { sessionId, textLength: text.length });

  try {
    // Nova Pro で応答テキスト生成
    const assistantText = await invokeNovaConverse(text);

    // TODO: Nova Sonic で音声合成（WebSocket 経由）
    // 現在はテキストレスポンスのみ

    const response: VoiceResponse = {
      userText: text,
      assistantText,
      metadata: {
        sessionId,
        model: NOVA_SONIC_MODEL_ID,
        timestamp: new Date().toISOString(),
      },
    };

    log('INFO', 'Voice response generated', { sessionId });
    return response;
  } catch (error) {
    log('ERROR', 'Voice processing failed', {
      error: error instanceof Error ? error.message : String(error),
    });

    return {
      userText: text,
      assistantText: 'I apologize, but I encountered an error processing your request.',
      metadata: {
        error: true,
        sessionId,
      },
    };
  }
}

/**
 * Voice Agent with audio input support
 * Supports TTS, STT, and full dialogue modes
 */
async function invokeVoiceAgent(args: InvokeVoiceAgentArgs): Promise<VoiceResponse> {
  const { sessionId, text, audio, mode = 'DIALOGUE' } = args;

  log('INFO', 'Invoking voice agent', { 
    sessionId, 
    mode, 
    hasText: !!text, 
    hasAudio: !!audio 
  });

  try {
    let transcription: string | undefined;
    let responseText: string | undefined;

    // Step 1: Speech-to-Text if audio provided
    if (audio && (mode === 'STT' || mode === 'DIALOGUE')) {
      log('DEBUG', 'Processing audio input for STT');
      // TODO: Use Nova Sonic or Amazon Transcribe for STT
      // For now, return placeholder
      transcription = '(音声認識は開発中です)';
    }

    // Step 2: Generate response text
    const inputText = text || transcription || '';
    if (inputText && (mode === 'TTS' || mode === 'DIALOGUE')) {
      responseText = await invokeNovaConverse(inputText);
    }

    // Step 3: Text-to-Speech if needed
    let responseAudio: string | undefined;
    if (responseText && (mode === 'TTS' || mode === 'DIALOGUE')) {
      // TODO: Use Nova Sonic or Amazon Polly for TTS
      // For now, no audio output
      log('DEBUG', 'TTS generation skipped (not yet implemented)');
    }

    const response: VoiceResponse = {
      transcript: transcription,
      userText: text,
      assistantText: responseText || (mode === 'STT' ? '文字起こし完了' : ''),
      audio: responseAudio,
      metadata: {
        sessionId,
        mode,
        timestamp: new Date().toISOString(),
      },
    };

    log('INFO', 'Voice agent response generated', { 
      sessionId, 
      hasTranscription: !!transcription,
      hasResponseText: !!responseText 
    });

    return response;
  } catch (error) {
    log('ERROR', 'Voice agent processing failed', {
      error: error instanceof Error ? error.message : String(error),
    });

    return {
      assistantText: 'エラーが発生しました。もう一度お試しください。',
      metadata: {
        error: true,
        sessionId,
        mode,
      },
    };
  }
}

/**
 * Nova Pro/Lite Converse API 呼び出し（画像分析対応）
 */
async function invokeNovaConverse(prompt: string, image?: string): Promise<string> {
  // Build message content
  const content: Array<{ text: string } | { image: { format: 'png' | 'jpeg' | 'gif' | 'webp'; source: { bytes: Uint8Array } } }> = [];
  
  // Add text prompt
  content.push({ text: prompt || 'この画像を詳しく説明してください。' });
  
  // Add image if provided (convert Base64 to Uint8Array)
  if (image) {
    try {
      // Decode Base64 to binary
      const binaryString = atob(image);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Detect image format from first bytes
      const format = detectImageFormat(bytes);
      
      content.push({
        image: {
          format,
          source: { bytes },
        },
      });
      
      log('DEBUG', 'Image attached to request', { 
        format, 
        sizeBytes: bytes.length 
      });
    } catch (error) {
      log('ERROR', 'Failed to decode image', { 
        error: error instanceof Error ? error.message : String(error) 
      });
    }
  }

  const messages = [
    {
      role: 'user' as const,
      content,
    },
  ];

  log('DEBUG', 'Sending Converse request', { 
    modelId: TEXT_MODEL_ID,
    hasImage: !!image,
    contentParts: content.length
  });

  const command = new ConverseCommand({
    modelId: TEXT_MODEL_ID,
    messages: messages as any,
    inferenceConfig: {
      maxTokens: 2048,
      temperature: 0.7,
    },
  });

  const response = await bedrockClient.send(command);
  const outputMessage = response.output?.message;

  if (outputMessage?.content?.[0] && 'text' in outputMessage.content[0]) {
    return outputMessage.content[0].text || '';
  }

  return '';
}

/**
 * Detect image format from binary data
 */
function detectImageFormat(bytes: Uint8Array): 'png' | 'jpeg' | 'gif' | 'webp' {
  // PNG: 89 50 4E 47
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47) {
    return 'png';
  }
  // JPEG: FF D8 FF
  if (bytes[0] === 0xFF && bytes[1] === 0xD8 && bytes[2] === 0xFF) {
    return 'jpeg';
  }
  // GIF: 47 49 46
  if (bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46) {
    return 'gif';
  }
  // WebP: 52 49 46 46 ... 57 45 42 50
  if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 &&
      bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50) {
    return 'webp';
  }
  // Default to jpeg (most common)
  return 'jpeg';
}

/**
 * Nova Canvas で画像生成
 */
async function invokeNovaCanvas(
  prompt: string
): Promise<{ base64: string; seed: number } | null> {
  try {
    const command = new InvokeModelCommand({
      modelId: NOVA_CANVAS_MODEL_ID,
      contentType: 'application/json',
      accept: 'application/json',
      body: JSON.stringify({
        taskType: 'TEXT_IMAGE',
        textToImageParams: {
          text: prompt,
        },
        imageGenerationConfig: {
          numberOfImages: 1,
          width: 1024,
          height: 1024,
          cfgScale: 8.0,
        },
      }),
    });

    const response = await bedrockClient.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    if (responseBody.images?.[0]) {
      return {
        base64: responseBody.images[0],
        seed: responseBody.seeds?.[0] || 0,
      };
    }

    return null;
  } catch (error) {
    log('WARN', 'Nova Canvas generation failed', {
      error: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

/**
 * 画像生成が必要かどうかを判定
 */
function shouldGenerateImage(prompt: string): boolean {
  const imageKeywords = [
    '画像を生成',
    '画像を作成',
    'generate image',
    'create image',
    'draw',
    '描いて',
    'イラスト',
  ];
  const lowerPrompt = prompt.toLowerCase();
  return imageKeywords.some((keyword) => lowerPrompt.includes(keyword.toLowerCase()));
}

/**
 * 動画生成が必要かどうかを判定
 */
function shouldGenerateVideo(prompt: string): boolean {
  const videoKeywords = [
    '動画を生成',
    '動画を作成',
    'generate video',
    'create video',
    'アニメーション',
  ];
  const lowerPrompt = prompt.toLowerCase();
  return videoKeywords.some((keyword) => lowerPrompt.includes(keyword.toLowerCase()));
}
