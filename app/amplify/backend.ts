/**
 * Amplify Gen2 Backend Definition
 *
 * rd-knowledge-sample プロジェクトのバックエンド定義
 *
 * アーキテクチャ:
 * - AppSync GraphQL API（CORS 問題解決）
 * - Lambda リゾルバ（Clean Architecture Infrastructure 層）
 * - AgentCore + StrandsAgents + BedrockAPI 構成
 * - DynamoDB（Memory永続化）
 * - S3（Vector保存）
 */

import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { memoryResolver } from './functions/memory-resolver/resource';
import { vectorResolver } from './functions/vector-resolver/resource';
import { graphResolver } from './functions/graph-resolver/resource';
import { agentResolver } from './functions/agent-resolver/resource';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { RemovalPolicy, Stack } from 'aws-cdk-lib';

const backend = defineBackend({
  auth,
  data,
  memoryResolver,
  vectorResolver,
  graphResolver,
  agentResolver,
});

// Get the underlying CDK stack
const stack = Stack.of(backend.memoryResolver.resources.lambda);

// ========================================
// DynamoDB Tables
// ========================================

// Memory Events Table (会話履歴)
const memoryEventsTable = new dynamodb.Table(stack, 'MemoryEventsTable', {
  tableName: `rd-knowledge-sample-memory-events-${stack.stackName}`,
  partitionKey: { name: 'sessionId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  removalPolicy: RemovalPolicy.DESTROY, // Dev only - use RETAIN for production
  pointInTimeRecovery: true,
});

// GSI for querying by actorId
memoryEventsTable.addGlobalSecondaryIndex({
  indexName: 'actorId-timestamp-index',
  partitionKey: { name: 'actorId', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
  projectionType: dynamodb.ProjectionType.ALL,
});

// Memory Sessions Table (セッション管理)
const memorySessionsTable = new dynamodb.Table(stack, 'MemorySessionsTable', {
  tableName: `rd-knowledge-sample-memory-sessions-${stack.stackName}`,
  partitionKey: { name: 'sessionId', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  removalPolicy: RemovalPolicy.DESTROY, // Dev only - use RETAIN for production
  timeToLiveAttribute: 'ttl',
});

// ========================================
// S3 Bucket for Vectors
// ========================================

const vectorBucket = new s3.Bucket(stack, 'VectorBucket', {
  bucketName: `rd-knowledge-sample-vectors-${stack.account}-${stack.region}`,
  removalPolicy: RemovalPolicy.DESTROY, // Dev only - use RETAIN for production
  autoDeleteObjects: true, // Dev only - remove for production
  versioned: false,
  encryption: s3.BucketEncryption.S3_MANAGED,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  cors: [
    {
      allowedHeaders: ['*'],
      allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT],
      allowedOrigins: ['*'], // Restrict in production
      maxAge: 3000,
    },
  ],
});

// ========================================
// Lambda IAM Permissions
// ========================================

// Bedrock permissions for agent resolver
const bedrockPolicy = new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    'bedrock:InvokeModel',
    'bedrock:InvokeModelWithResponseStream',
    'bedrock:Converse',
    'bedrock:ConverseStream',
  ],
  resources: ['*'],
});

// DynamoDB permissions (scoped to created tables)
const dynamoPolicy = new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    'dynamodb:GetItem',
    'dynamodb:PutItem',
    'dynamodb:UpdateItem',
    'dynamodb:DeleteItem',
    'dynamodb:Query',
    'dynamodb:Scan',
  ],
  resources: [
    memoryEventsTable.tableArn,
    `${memoryEventsTable.tableArn}/index/*`,
    memorySessionsTable.tableArn,
  ],
});

// S3 permissions (scoped to created bucket)
const s3Policy = new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    's3:GetObject',
    's3:PutObject',
    's3:ListBucket',
    's3:DeleteObject',
  ],
  resources: [
    vectorBucket.bucketArn,
    `${vectorBucket.bucketArn}/*`,
  ],
});

// ========================================
// Add permissions to resolvers
// ========================================

// Agent Resolver: Bedrock + S3
backend.agentResolver.resources.lambda.addToRolePolicy(bedrockPolicy);
backend.agentResolver.resources.lambda.addToRolePolicy(s3Policy);

// Vector Resolver: Bedrock (embeddings) + S3
backend.vectorResolver.resources.lambda.addToRolePolicy(bedrockPolicy);
backend.vectorResolver.resources.lambda.addToRolePolicy(s3Policy);

// Memory Resolver: DynamoDB
backend.memoryResolver.resources.lambda.addToRolePolicy(dynamoPolicy);

// Graph Resolver: DynamoDB
backend.graphResolver.resources.lambda.addToRolePolicy(dynamoPolicy);

// ========================================
// Environment Variables
// ========================================

// Memory Resolver
backend.memoryResolver.resources.lambda.addEnvironment('MEMORY_TABLE', memoryEventsTable.tableName);
backend.memoryResolver.resources.lambda.addEnvironment('SESSION_TABLE', memorySessionsTable.tableName);

// Vector Resolver
backend.vectorResolver.resources.lambda.addEnvironment('OUTPUT_BUCKET', vectorBucket.bucketName);

// Agent Resolver
backend.agentResolver.resources.lambda.addEnvironment('OUTPUT_BUCKET', vectorBucket.bucketName);

export default backend;
