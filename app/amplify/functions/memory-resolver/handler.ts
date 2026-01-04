/**
 * Memory Resolver Lambda Handler
 *
 * DynamoDB を使用した会話履歴管理
 * (AgentCore Memory SDK 正式リリース後に移行予定)
 *
 * 設計原則:
 * - 12 Factor App Agents 準拠
 * - CloudTrail / X-Ray 追跡可能
 * - Clean Architecture: Infrastructure 層として Domain 層を呼び出す
 */

import type { AppSyncResolverHandler } from 'aws-lambda';
import {
  DynamoDBClient,
  PutItemCommand,
  QueryCommand,
  DeleteItemCommand,
  ScanCommand,
} from '@aws-sdk/client-dynamodb';
import { marshall, unmarshall } from '@aws-sdk/util-dynamodb';

// Types aligned with Domain Layer
interface MemoryEvent {
  id: string;
  actorId: string;
  sessionId: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

interface MemorySession {
  sessionId: string;
  startTime: string;
  endTime?: string;
  title?: string;
  tags?: string[];
}

interface GetMemoryEventsArgs {
  actorId: string;
  sessionId?: string;
  limit?: number;
}

interface CreateMemoryEventArgs {
  actorId: string;
  sessionId: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  metadata?: Record<string, unknown>;
}

interface GetMemorySessionArgs {
  sessionId: string;
}

interface DeleteMemorySessionArgs {
  sessionId: string;
}

interface CreateMemorySessionArgs {
  title?: string;
  tags?: string[];
}

type ResolverArgs =
  | GetMemoryEventsArgs
  | CreateMemoryEventArgs
  | GetMemorySessionArgs
  | DeleteMemorySessionArgs
  | CreateMemorySessionArgs;

// Environment
const REGION = process.env.AWS_REGION || 'ap-northeast-1';
const MEMORY_TABLE = process.env.MEMORY_TABLE || 'MemoryEvents';
const SESSION_TABLE = process.env.SESSION_TABLE || 'MemorySessions';
const LOG_LEVEL = process.env.LOG_LEVEL || 'INFO';

// DynamoDB Client
const dynamoClient = new DynamoDBClient({ region: REGION });

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
        service: 'memory-resolver',
      })
    );
  }
};

export const handler: AppSyncResolverHandler<
  ResolverArgs,
  MemoryEvent | MemoryEvent[] | MemorySession | boolean
> = async (event) => {
  // Amplify Gen2 handler structure: fieldName is directly on event
  const fieldName = (event as any).fieldName || event.info?.fieldName;
  const args = (event as any).arguments || event.arguments;

  log('INFO', 'Memory Resolver invoked', {
    fieldName,
    eventKeys: Object.keys(event),
  });

  try {
    switch (fieldName) {
      case 'getMemoryEvents':
        return await getMemoryEvents(args as GetMemoryEventsArgs);
      case 'getMemorySession':
        return await getMemorySession(args as GetMemorySessionArgs);
      case 'createMemorySession':
        return await createMemorySession(args as CreateMemorySessionArgs);
      case 'createMemoryEvent':
        return await createMemoryEvent(args as CreateMemoryEventArgs);
      case 'deleteMemorySession':
        return await deleteMemorySession(args as DeleteMemorySessionArgs);
      default:
        throw new Error(`Unknown field: ${fieldName}`);
    }
  } catch (error) {
    log('ERROR', 'Memory Resolver failed', {
      error: error instanceof Error ? error.message : String(error),
      fieldName,
    });
    throw error;
  }
};

/**
 * DynamoDB からメモリイベント取得
 */
async function getMemoryEvents(args: GetMemoryEventsArgs): Promise<MemoryEvent[]> {
  const { actorId, sessionId, limit = 50 } = args;

  log('DEBUG', 'Getting memory events', { actorId, sessionId, limit });

  try {
    // セッションIDが指定されている場合はそのセッションのイベントのみ取得
    if (sessionId) {
      const command = new QueryCommand({
        TableName: MEMORY_TABLE,
        KeyConditionExpression: 'sessionId = :sid',
        ExpressionAttributeValues: marshall({
          ':sid': sessionId,
        }),
        Limit: limit,
        ScanIndexForward: true, // 古い順
      });

      const result = await dynamoClient.send(command);
      const events = (result.Items || []).map((item) => unmarshall(item) as MemoryEvent);

      log('INFO', 'Memory events retrieved by session', { count: events.length, sessionId });
      return events;
    }

    // actorIdでフィルター（GSI使用を推奨）
    const command = new QueryCommand({
      TableName: MEMORY_TABLE,
      IndexName: 'actorId-timestamp-index',
      KeyConditionExpression: 'actorId = :aid',
      ExpressionAttributeValues: marshall({
        ':aid': actorId,
      }),
      Limit: limit,
      ScanIndexForward: false, // 新しい順
    });

    const result = await dynamoClient.send(command);
    const events = (result.Items || []).map((item) => unmarshall(item) as MemoryEvent);

    log('INFO', 'Memory events retrieved by actor', { count: events.length, actorId });
    return events;
  } catch (error) {
    log('ERROR', 'Failed to get memory events', {
      error: error instanceof Error ? error.message : String(error),
    });

    // テーブルが存在しない場合は空の配列を返す
    if ((error as any).name === 'ResourceNotFoundException') {
      log('WARN', 'Memory table not found, returning empty array');
      return [];
    }

    throw error;
  }
}

/**
 * セッション情報取得
 */
async function getMemorySession(args: GetMemorySessionArgs): Promise<MemorySession> {
  const { sessionId } = args;

  log('DEBUG', 'Getting memory session', { sessionId });

  try {
    const command = new QueryCommand({
      TableName: SESSION_TABLE,
      KeyConditionExpression: 'sessionId = :sid',
      ExpressionAttributeValues: marshall({
        ':sid': sessionId,
      }),
      Limit: 1,
    });

    const result = await dynamoClient.send(command);

    if (result.Items && result.Items.length > 0) {
      const session = unmarshall(result.Items[0]) as MemorySession;
      log('INFO', 'Session found', { sessionId });
      return session;
    }

    // セッションが見つからない場合は新規作成
    log('INFO', 'Session not found, creating new', { sessionId });
    return await createMemorySession({ title: `Session ${sessionId}` });
  } catch (error) {
    log('ERROR', 'Failed to get session', {
      error: error instanceof Error ? error.message : String(error),
    });

    // テーブルが存在しない場合はダミーセッションを返す
    if ((error as any).name === 'ResourceNotFoundException') {
      return {
        sessionId,
        startTime: new Date().toISOString(),
        title: `Session ${sessionId}`,
        tags: [],
      };
    }

    throw error;
  }
}

/**
 * 新規セッション作成
 */
async function createMemorySession(args: CreateMemorySessionArgs): Promise<MemorySession> {
  const { title, tags } = args;

  const sessionId = `sess-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const session: MemorySession = {
    sessionId,
    startTime: new Date().toISOString(),
    title: title || 'New Session',
    tags: tags || [],
  };

  log('DEBUG', 'Creating memory session', { sessionId, title });

  try {
    const command = new PutItemCommand({
      TableName: SESSION_TABLE,
      Item: marshall(session),
    });

    await dynamoClient.send(command);
    log('INFO', 'Memory session created', { sessionId });
    return session;
  } catch (error) {
    log('ERROR', 'Failed to create session', {
      error: error instanceof Error ? error.message : String(error),
    });

    // テーブルが存在しなくてもセッションオブジェクトは返す（メモリ内で管理）
    if ((error as any).name === 'ResourceNotFoundException') {
      log('WARN', 'Session table not found, returning in-memory session');
      return session;
    }

    throw error;
  }
}

/**
 * メモリイベント作成
 */
async function createMemoryEvent(args: CreateMemoryEventArgs): Promise<MemoryEvent> {
  const { actorId, sessionId, role, content, metadata } = args;

  const event: MemoryEvent = {
    id: `evt-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    actorId,
    sessionId,
    role,
    content,
    timestamp: new Date().toISOString(),
    metadata,
  };

  log('DEBUG', 'Creating memory event', { actorId, sessionId, role, contentLength: content.length });

  try {
    const command = new PutItemCommand({
      TableName: MEMORY_TABLE,
      Item: marshall(event, { removeUndefinedValues: true }),
    });

    await dynamoClient.send(command);
    log('INFO', 'Memory event created', { eventId: event.id, role });
    return event;
  } catch (error) {
    log('ERROR', 'Failed to create event', {
      error: error instanceof Error ? error.message : String(error),
    });

    // テーブルが存在しなくてもイベントオブジェクトは返す（ログには記録される）
    if ((error as any).name === 'ResourceNotFoundException') {
      log('WARN', 'Memory table not found, returning in-memory event');
      return event;
    }

    throw error;
  }
}

/**
 * セッション削除
 */
async function deleteMemorySession(args: DeleteMemorySessionArgs): Promise<boolean> {
  const { sessionId } = args;

  log('DEBUG', 'Deleting memory session', { sessionId });

  try {
    // セッション削除
    const deleteSessionCommand = new DeleteItemCommand({
      TableName: SESSION_TABLE,
      Key: marshall({ sessionId }),
    });
    await dynamoClient.send(deleteSessionCommand);

    // 関連イベント削除（セッションに紐づくイベントをすべて削除）
    const queryCommand = new QueryCommand({
      TableName: MEMORY_TABLE,
      KeyConditionExpression: 'sessionId = :sid',
      ExpressionAttributeValues: marshall({ ':sid': sessionId }),
    });

    const result = await dynamoClient.send(queryCommand);
    
    if (result.Items) {
      for (const item of result.Items) {
        const event = unmarshall(item);
        const deleteEventCommand = new DeleteItemCommand({
          TableName: MEMORY_TABLE,
          Key: marshall({ sessionId: event.sessionId, timestamp: event.timestamp }),
        });
        await dynamoClient.send(deleteEventCommand);
      }
    }

    log('INFO', 'Memory session deleted', { sessionId, eventsDeleted: result.Items?.length || 0 });
    return true;
  } catch (error) {
    log('ERROR', 'Failed to delete session', {
      error: error instanceof Error ? error.message : String(error),
    });

    // テーブルが存在しない場合も成功を返す
    if ((error as any).name === 'ResourceNotFoundException') {
      return true;
    }

    throw error;
  }
}
