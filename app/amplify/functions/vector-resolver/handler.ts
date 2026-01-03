/**
 * Vector Resolver Lambda Handler
 *
 * S3 Vector Store を使用したベクトル検索
 * (OpenSearch は Enterprise Scale のみ使用)
 *
 * 設計原則:
 * - AgentCore + StrandsAgents + BedrockAPI 構成
 * - S3Vector でコスト最小化
 * - AgentCore_Observability / CloudTrail 追跡可能
 */

import type { AppSyncResolverHandler } from 'aws-lambda';
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from '@aws-sdk/client-bedrock-runtime';
import { S3Client, PutObjectCommand, GetObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';

// Types aligned with Domain Layer
interface Vector {
  id: string;
  content: string;
  vector: number[];
  metadata?: Record<string, unknown>;
}

interface SearchVectorsArgs {
  query: string;
  k?: number;
  minScore?: number;
}

interface IndexDocumentArgs {
  id?: string;
  content: string;
  metadata?: Record<string, unknown>;
}

type ResolverArgs = SearchVectorsArgs | IndexDocumentArgs;

// Environment
const REGION = process.env.AWS_REGION || 'ap-northeast-1';
const OUTPUT_BUCKET = process.env.OUTPUT_BUCKET || '';
const LOG_LEVEL = process.env.LOG_LEVEL || 'INFO';

// Model for embeddings
const TITAN_EMBED_MODEL_ID = 'amazon.titan-embed-text-v2:0';

// Clients
const bedrockClient = new BedrockRuntimeClient({ region: REGION });
const s3Client = new S3Client({ region: REGION });

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
        service: 'vector-resolver',
      })
    );
  }
};

export const handler: AppSyncResolverHandler<ResolverArgs, Vector | Vector[]> = async (event) => {
  // Amplify Gen2 handler structure: fieldName is directly on event
  const fieldName = (event as any).fieldName || event.info?.fieldName;
  const args = (event as any).arguments || event.arguments;

  log('INFO', 'Vector Resolver invoked', {
    fieldName,
    eventKeys: Object.keys(event),
  });

  try {
    switch (fieldName) {
      case 'searchVectors':
        return await searchVectors(args as SearchVectorsArgs);
      case 'indexDocument':
        return await indexDocument(args as IndexDocumentArgs);
      default:
        throw new Error(`Unknown field: ${fieldName}`);
    }
  } catch (error) {
    log('ERROR', 'Vector Resolver failed', {
      error: error instanceof Error ? error.message : String(error),
      fieldName,
    });
    throw error;
  }
};

/**
 * ベクトル検索
 * S3 に保存されたベクトルをスキャンしてコサイン類似度で検索
 */
async function searchVectors(args: SearchVectorsArgs): Promise<Vector[]> {
  const { query, k = 5, minScore = 0.7 } = args;

  log('INFO', 'Searching vectors', { query, k, minScore });

  // Step 1: クエリをベクトル化
  const queryVector = await generateEmbedding(query);

  // Step 2: S3 からベクトルインデックスを読み込み
  const vectors = await loadVectorsFromS3();

  // Step 3: コサイン類似度でランキング
  const results = vectors
    .map((vec) => ({
      ...vec,
      score: cosineSimilarity(queryVector, vec.vector),
    }))
    .filter((vec) => vec.score >= minScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);

  log('INFO', 'Search completed', { resultCount: results.length });

  return results.map(({ score, ...vec }) => vec);
}

/**
 * ドキュメントをインデックス
 */
async function indexDocument(args: IndexDocumentArgs): Promise<Vector> {
  const { id, content, metadata } = args;

  log('INFO', 'Indexing document', { id, contentLength: content.length });

  // Step 1: コンテンツをベクトル化
  const vector = await generateEmbedding(content);

  // Step 2: ベクトルをS3に保存
  const docId = id || `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const vectorDoc: Vector = {
    id: docId,
    content,
    vector,
    metadata: {
      ...metadata,
      indexedAt: new Date().toISOString(),
    },
  };

  await saveVectorToS3(vectorDoc);

  log('INFO', 'Document indexed', { docId });

  return vectorDoc;
}

/**
 * Titan Embeddings でテキストをベクトル化
 */
async function generateEmbedding(text: string): Promise<number[]> {
  const command = new InvokeModelCommand({
    modelId: TITAN_EMBED_MODEL_ID,
    contentType: 'application/json',
    accept: 'application/json',
    body: JSON.stringify({
      inputText: text,
    }),
  });

  const response = await bedrockClient.send(command);
  const responseBody = JSON.parse(new TextDecoder().decode(response.body));

  return responseBody.embedding;
}

/**
 * S3 からベクトルを読み込み
 */
async function loadVectorsFromS3(): Promise<Vector[]> {
  if (!OUTPUT_BUCKET) {
    log('WARN', 'OUTPUT_BUCKET not configured, returning empty');
    return [];
  }

  try {
    const listCommand = new ListObjectsV2Command({
      Bucket: OUTPUT_BUCKET,
      Prefix: 'vectors/',
    });

    const listResponse = await s3Client.send(listCommand);
    const vectors: Vector[] = [];

    if (listResponse.Contents) {
      for (const obj of listResponse.Contents) {
        if (obj.Key) {
          const getCommand = new GetObjectCommand({
            Bucket: OUTPUT_BUCKET,
            Key: obj.Key,
          });

          const getResponse = await s3Client.send(getCommand);
          const body = await getResponse.Body?.transformToString();

          if (body) {
            vectors.push(JSON.parse(body));
          }
        }
      }
    }

    return vectors;
  } catch (error) {
    log('ERROR', 'Failed to load vectors from S3', {
      error: error instanceof Error ? error.message : String(error),
    });
    return [];
  }
}

/**
 * ベクトルを S3 に保存
 */
async function saveVectorToS3(vector: Vector): Promise<void> {
  if (!OUTPUT_BUCKET) {
    log('WARN', 'OUTPUT_BUCKET not configured, skipping save');
    return;
  }

  const command = new PutObjectCommand({
    Bucket: OUTPUT_BUCKET,
    Key: `vectors/${vector.id}.json`,
    Body: JSON.stringify(vector),
    ContentType: 'application/json',
  });

  await s3Client.send(command);
}

/**
 * コサイン類似度計算
 */
function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Vector dimensions must match');
  }

  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }

  const denominator = Math.sqrt(normA) * Math.sqrt(normB);
  if (denominator === 0) return 0;

  return dotProduct / denominator;
}
