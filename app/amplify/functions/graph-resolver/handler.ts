/**
 * Graph Resolver Lambda Handler
 *
 * DynamoDB + Neptune (将来) でグラフデータを管理
 * 現在は DynamoDB で隣接リスト形式で実装
 *
 * 設計原則:
 * - AgentCore + StrandsAgents + BedrockAPI 構成
 * - コスト最小化のため DynamoDB を使用
 * - AgentCore_Observability / CloudTrail 追跡可能
 */

import type { AppSyncResolverHandler } from 'aws-lambda';
import {
  DynamoDBClient,
  PutItemCommand,
  GetItemCommand,
  QueryCommand,
  DeleteItemCommand,
  ScanCommand,
} from '@aws-sdk/client-dynamodb';
import { marshall, unmarshall } from '@aws-sdk/util-dynamodb';

// Types aligned with Domain Layer
interface Node {
  id: string;
  type: string;
  properties: Record<string, unknown>;
}

interface Edge {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
  properties: Record<string, unknown>;
}

interface CreateNodeArgs {
  type: string;
  properties?: Record<string, unknown>;
}

interface GetNodeArgs {
  id: string;
}

interface GetNodesArgs {
  type?: string;
}

interface UpdateNodeArgs {
  id: string;
  properties: Record<string, unknown>;
}

interface DeleteNodeArgs {
  id: string;
}

interface CreateEdgeArgs {
  sourceId: string;
  targetId: string;
  type: string;
  properties?: Record<string, unknown>;
}

interface DeleteEdgeArgs {
  id: string;
}

interface QueryGraphArgs {
  cypherQuery: string;
}

type ResolverArgs =
  | CreateNodeArgs
  | GetNodeArgs
  | GetNodesArgs
  | UpdateNodeArgs
  | DeleteNodeArgs
  | CreateEdgeArgs
  | DeleteEdgeArgs
  | QueryGraphArgs;

// Environment
const REGION = process.env.AWS_REGION || 'ap-northeast-1';
const NODES_TABLE = process.env.NODES_TABLE || 'rd-knowledge-nodes';
const EDGES_TABLE = process.env.EDGES_TABLE || 'rd-knowledge-edges';
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
        service: 'graph-resolver',
      })
    );
  }
};

export const handler: AppSyncResolverHandler<
  ResolverArgs,
  Node | Node[] | Edge | Record<string, unknown> | null
> = async (event) => {
  // Amplify Gen2 handler structure: fieldName is directly on event
  const fieldName = (event as any).fieldName || event.info?.fieldName;
  const args = (event as any).arguments || event.arguments;

  log('INFO', 'Graph Resolver invoked', {
    fieldName,
    eventKeys: Object.keys(event),
  });

  try {
    switch (fieldName) {
      case 'createNode':
        return await createNode(args as CreateNodeArgs);
      case 'getNode':
        return await getNode(args as GetNodeArgs);
      case 'getNodes':
        return await getNodes(args as GetNodesArgs);
      case 'updateNode':
        return await updateNode(args as UpdateNodeArgs);
      case 'deleteNode':
        return await deleteNode(args as DeleteNodeArgs);
      case 'createEdge':
        return await createEdge(args as CreateEdgeArgs);
      case 'deleteEdge':
        return await deleteEdge(args as DeleteEdgeArgs);
      case 'queryGraph':
        return await queryGraph(args as QueryGraphArgs);
      default:
        throw new Error(`Unknown field: ${fieldName}`);
    }
  } catch (error) {
    log('ERROR', 'Graph Resolver failed', {
      error: error instanceof Error ? error.message : String(error),
      fieldName,
    });
    throw error;
  }
};

/**
 * ノード作成
 */
async function createNode(args: CreateNodeArgs): Promise<Node> {
  const { type, properties = {} } = args;

  const id = `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const node: Node = {
    id,
    type,
    properties: {
      ...properties,
      createdAt: new Date().toISOString(),
    },
  };

  log('DEBUG', 'Creating node', { id, type });

  const command = new PutItemCommand({
    TableName: NODES_TABLE,
    Item: marshall({
      pk: id,
      sk: 'NODE',
      gsi1pk: type,
      gsi1sk: id,
      ...node,
    }),
  });

  await dynamoClient.send(command);

  log('INFO', 'Node created', { id, type });
  return node;
}

/**
 * ノード取得
 */
async function getNode(args: GetNodeArgs): Promise<Node | null> {
  const { id } = args;

  log('DEBUG', 'Getting node', { id });

  const command = new GetItemCommand({
    TableName: NODES_TABLE,
    Key: marshall({
      pk: id,
      sk: 'NODE',
    }),
  });

  const response = await dynamoClient.send(command);

  if (!response.Item) {
    return null;
  }

  const item = unmarshall(response.Item);
  return {
    id: item.id,
    type: item.type,
    properties: item.properties,
  };
}

/**
 * ノード一覧取得
 */
async function getNodes(args: GetNodesArgs): Promise<Node[]> {
  const { type } = args;

  log('DEBUG', 'Getting nodes', { type });

  let command;

  if (type) {
    // GSI でタイプ別にクエリ
    command = new QueryCommand({
      TableName: NODES_TABLE,
      IndexName: 'gsi1',
      KeyConditionExpression: 'gsi1pk = :type',
      ExpressionAttributeValues: marshall({
        ':type': type,
      }),
    });
  } else {
    // 全スキャン
    command = new ScanCommand({
      TableName: NODES_TABLE,
      FilterExpression: 'sk = :sk',
      ExpressionAttributeValues: marshall({
        ':sk': 'NODE',
      }),
    });
  }

  const response = await dynamoClient.send(command);

  const nodes = (response.Items || []).map((item: Record<string, any>) => {
    const unmarshalled = unmarshall(item);
    return {
      id: unmarshalled.id,
      type: unmarshalled.type,
      properties: unmarshalled.properties,
    };
  });

  log('INFO', 'Nodes retrieved', { count: nodes.length });
  return nodes;
}

/**
 * ノード更新
 */
async function updateNode(args: UpdateNodeArgs): Promise<Node | null> {
  const { id, properties } = args;

  log('DEBUG', 'Updating node', { id });

  // まず既存ノードを取得
  const existing = await getNode({ id });
  if (!existing) {
    return null;
  }

  const updatedNode: Node = {
    ...existing,
    properties: {
      ...existing.properties,
      ...properties,
      updatedAt: new Date().toISOString(),
    },
  };

  const command = new PutItemCommand({
    TableName: NODES_TABLE,
    Item: marshall({
      pk: id,
      sk: 'NODE',
      gsi1pk: updatedNode.type,
      gsi1sk: id,
      ...updatedNode,
    }),
  });

  await dynamoClient.send(command);

  log('INFO', 'Node updated', { id });
  return updatedNode;
}

/**
 * ノード削除
 */
async function deleteNode(args: DeleteNodeArgs): Promise<Node | null> {
  const { id } = args;

  log('DEBUG', 'Deleting node', { id });

  const existing = await getNode({ id });
  if (!existing) {
    return null;
  }

  const command = new DeleteItemCommand({
    TableName: NODES_TABLE,
    Key: marshall({
      pk: id,
      sk: 'NODE',
    }),
  });

  await dynamoClient.send(command);

  // 関連エッジも削除
  await deleteEdgesByNode(id);

  log('INFO', 'Node deleted', { id });
  return existing;
}

/**
 * エッジ作成
 */
async function createEdge(args: CreateEdgeArgs): Promise<Edge> {
  const { sourceId, targetId, type, properties = {} } = args;

  const id = `edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const edge: Edge = {
    id,
    sourceId,
    targetId,
    type,
    properties: {
      ...properties,
      createdAt: new Date().toISOString(),
    },
  };

  log('DEBUG', 'Creating edge', { id, sourceId, targetId, type });

  const command = new PutItemCommand({
    TableName: EDGES_TABLE,
    Item: marshall({
      pk: sourceId,
      sk: `EDGE#${targetId}#${id}`,
      gsi1pk: targetId,
      gsi1sk: `EDGE#${sourceId}#${id}`,
      ...edge,
    }),
  });

  await dynamoClient.send(command);

  log('INFO', 'Edge created', { id });
  return edge;
}

/**
 * エッジ削除
 */
async function deleteEdge(args: DeleteEdgeArgs): Promise<Edge | null> {
  const { id } = args;

  log('DEBUG', 'Deleting edge', { id });

  // エッジを検索して削除
  // 実装簡略化のため、スキャンで検索
  const scanCommand = new ScanCommand({
    TableName: EDGES_TABLE,
    FilterExpression: 'id = :id',
    ExpressionAttributeValues: marshall({
      ':id': id,
    }),
  });

  const response = await dynamoClient.send(scanCommand);

  if (!response.Items || response.Items.length === 0) {
    return null;
  }

  const item = unmarshall(response.Items[0]);

  const deleteCommand = new DeleteItemCommand({
    TableName: EDGES_TABLE,
    Key: marshall({
      pk: item.pk,
      sk: item.sk,
    }),
  });

  await dynamoClient.send(deleteCommand);

  log('INFO', 'Edge deleted', { id });
  return {
    id: item.id,
    sourceId: item.sourceId,
    targetId: item.targetId,
    type: item.type,
    properties: item.properties,
  };
}

/**
 * ノードに関連するエッジをすべて削除
 */
async function deleteEdgesByNode(nodeId: string): Promise<void> {
  log('DEBUG', 'Deleting edges for node', { nodeId });

  // sourceId として検索
  const queryCommand = new QueryCommand({
    TableName: EDGES_TABLE,
    KeyConditionExpression: 'pk = :pk',
    ExpressionAttributeValues: marshall({
      ':pk': nodeId,
    }),
  });

  const response = await dynamoClient.send(queryCommand);

  for (const item of response.Items || []) {
    const unmarshalled = unmarshall(item);
    const deleteCommand = new DeleteItemCommand({
      TableName: EDGES_TABLE,
      Key: marshall({
        pk: unmarshalled.pk,
        sk: unmarshalled.sk,
      }),
    });
    await dynamoClient.send(deleteCommand);
  }

  // targetId として検索（GSI 使用）
  const gsiQueryCommand = new QueryCommand({
    TableName: EDGES_TABLE,
    IndexName: 'gsi1',
    KeyConditionExpression: 'gsi1pk = :pk',
    ExpressionAttributeValues: marshall({
      ':pk': nodeId,
    }),
  });

  const gsiResponse = await dynamoClient.send(gsiQueryCommand);

  for (const item of gsiResponse.Items || []) {
    const unmarshalled = unmarshall(item);
    const deleteCommand = new DeleteItemCommand({
      TableName: EDGES_TABLE,
      Key: marshall({
        pk: unmarshalled.pk,
        sk: unmarshalled.sk,
      }),
    });
    await dynamoClient.send(deleteCommand);
  }
}

/**
 * グラフクエリ（簡易版）
 * 本格的な Cypher クエリは Neptune 移行後に実装
 */
async function queryGraph(args: QueryGraphArgs): Promise<Record<string, unknown>> {
  const { cypherQuery } = args;

  log('DEBUG', 'Executing graph query', { cypherQuery });

  // 簡易的なクエリパーサー
  // MATCH (n:Type) RETURN n の形式のみサポート

  const matchPattern = /MATCH\s*\(\s*\w+\s*:\s*(\w+)\s*\)/i;
  const match = cypherQuery.match(matchPattern);

  if (match) {
    const type = match[1];
    const nodes = await getNodes({ type });
    return { nodes };
  }

  // 未サポートのクエリ
  return {
    message: 'Query executed (simplified parser)',
    query: cypherQuery,
    note: 'Full Cypher support available after Neptune migration',
  };
}
