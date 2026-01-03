/**
 * Amplify Gen2 Backend Definition
 *
 * rd-knowledge-sample プロジェクトのバックエンド定義
 *
 * アーキテクチャ:
 * - AppSync GraphQL API（CORS 問題解決）
 * - Lambda リゾルバ（Clean Architecture Infrastructure 層）
 * - AgentCore + StrandsAgents + BedrockAPI 構成
 */

import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { memoryResolver } from './functions/memory-resolver/resource';
import { vectorResolver } from './functions/vector-resolver/resource';
import { graphResolver } from './functions/graph-resolver/resource';
import { agentResolver } from './functions/agent-resolver/resource';
import * as iam from 'aws-cdk-lib/aws-iam';

const backend = defineBackend({
  auth,
  data,
  memoryResolver,
  vectorResolver,
  graphResolver,
  agentResolver,
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

// S3 permissions for vector resolver
const s3Policy = new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    's3:GetObject',
    's3:PutObject',
    's3:ListBucket',
    's3:DeleteObject',
  ],
  resources: ['*'], // Should be scoped to specific bucket in production
});

// DynamoDB permissions for graph resolver
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
  resources: ['*'], // Should be scoped to specific tables in production
});

// Add permissions to resolvers
backend.agentResolver.resources.lambda.addToRolePolicy(bedrockPolicy);
backend.agentResolver.resources.lambda.addToRolePolicy(s3Policy);

backend.vectorResolver.resources.lambda.addToRolePolicy(bedrockPolicy);
backend.vectorResolver.resources.lambda.addToRolePolicy(s3Policy);

backend.memoryResolver.resources.lambda.addToRolePolicy(s3Policy);

backend.graphResolver.resources.lambda.addToRolePolicy(dynamoPolicy);

export default backend;
