# Amplify Gen2 + AppSync 移行設計ドキュメント

## 1. 概要

### 1.1 移行の目的

API Gateway (REST) + CloudFront/S3 から **Amplify Gen2 + AppSync (GraphQL)** への移行により、以下を実現する：

1. **統合アーキテクチャ**: フロントエンド・バックエンドを Amplify Gen2 で一元管理
2. **GraphQL 単一エンドポイント**: 複数 REST API を統合
3. **リアルタイム通信**: Voice Dialogue に AppSync Subscriptions を活用
4. **自動 CI/CD**: Git Push で自動デプロイ（Amplify Hosting）
5. **型安全**: TypeScript スキーマ定義から自動生成
6. **CORS 自動対応**: AppSync は CORS を自動処理

### 1.2 設計原則

```
✅ AgentCore + StrandsAgents + BedrockAPI 構成を厳守
✅ AgentCore_Observability / CloudTrail で追跡可能
✅ AgentCore_memory + S3Vector でコスト最小化
✅ OpenSearch 不採用（エンタープライズ規模でないため）
✅ Amplify Gen2 TypeScript-first アプローチ
❌ boto3 / cli / script / sh 直接処理禁止
❌ LangChain 等の他パッケージ禁止
```

## 2. ディレクトリ構造

```
rd-knowledge-sample/
├── app/                          # Next.js フロントエンド
│   ├── amplify/                  # 🆕 Amplify Gen2 バックエンド定義
│   │   ├── auth/
│   │   │   └── resource.ts       # Cognito 認証設定
│   │   ├── data/
│   │   │   └── resource.ts       # AppSync スキーマ定義
│   │   ├── functions/
│   │   │   ├── memory-resolver/
│   │   │   │   ├── handler.ts    # AgentCore Memory 操作
│   │   │   │   └── resource.ts
│   │   │   ├── vector-resolver/
│   │   │   │   ├── handler.ts    # S3 Vector 操作
│   │   │   │   └── resource.ts
│   │   │   ├── graph-resolver/
│   │   │   │   ├── handler.ts    # Neo4j 操作
│   │   │   │   └── resource.ts
│   │   │   └── agent-resolver/
│   │   │       ├── handler.ts    # StrandsAgents Multimodal/Voice
│   │   │       └── resource.ts
│   │   ├── storage/
│   │   │   └── resource.ts       # S3 ストレージ設定
│   │   └── backend.ts            # バックエンド統合エントリ
│   ├── components/               # React コンポーネント
│   ├── lib/
│   │   └── amplify-config.ts     # Amplify クライアント設定
│   ├── graphql/                  # 生成された GraphQL operations
│   ├── page.tsx
│   ├── layout.tsx
│   └── amplify_outputs.json      # 🔧 Amplify 自動生成（.gitignore）
├── infra/                        # 🔄 既存 CDK（段階的廃止）
├── src/                          # Python バックエンドロジック
│   └── agents/                   # StrandsAgents 実装
├── docs/
├── tests/
└── package.json
```

## 3. アーキテクチャ

### 3.1 現行アーキテクチャ（廃止予定）

```
┌─────────────┐     ┌─────────────────────────────────────────┐
│  Frontend   │────▶│  CloudFront + S3 (CDK)                  │
│  (Next.js)  │     └─────────────────────────────────────────┘
└─────────────┘                    │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
            ┌───────────────┐             ┌───────────────┐
            │  API Gateway  │             │  Lambda       │
            │  (REST)       │────────────▶│  (複数)       │
            └───────────────┘             └───────────────┘
```

### 3.2 新アーキテクチャ（Amplify Gen2）

```
┌─────────────┐     ┌─────────────────────────────────────────┐
│  Frontend   │────▶│  Amplify Hosting (CI/CD込み)            │
│  (Next.js + │     │  - Git Push で自動デプロイ              │
│  Amplify)   │     │  - Branch ごとに環境分離                │
└─────────────┘     └─────────────────────────────────────────┘
       │                              │
       │ GraphQL                      │ 自動生成
       ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS AppSync (GraphQL)                                      │
│  - Query/Mutation: Lambda Resolver                          │
│  - Subscription: Real-time WebSocket (Voice Dialogue)       │
│  - X-Ray/CloudTrail 追跡                                    │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │ Memory    │       │ Vector    │       │ Agent     │
    │ Resolver  │       │ Resolver  │       │ Resolver  │
    └───────────┘       └───────────┘       └───────────┘
          │                   │                   │
          ▼                   ▼                   ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │ AgentCore │       │ S3 Vector │       │ Strands   │
    │ Memory    │       │           │       │ Agents    │
    └───────────┘       └───────────┘       └───────────┘
```

## 4. Amplify Gen2 実装

### 4.1 バックエンド定義 (`app/amplify/backend.ts`)

```typescript
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';
import { memoryResolver } from './functions/memory-resolver/resource';
import { vectorResolver } from './functions/vector-resolver/resource';
import { graphResolver } from './functions/graph-resolver/resource';
import { agentResolver } from './functions/agent-resolver/resource';

export const backend = defineBackend({
  auth,
  data,
  storage,
  memoryResolver,
  vectorResolver,
  graphResolver,
  agentResolver,
});

// X-Ray トレーシング有効化
backend.data.resources.graphqlApi.xrayEnabled = true;
```

### 4.2 認証設定 (`app/amplify/auth/resource.ts`)

```typescript
import { defineAuth } from '@aws-amplify/backend';

export const auth = defineAuth({
  loginWith: {
    email: true,
  },
  // API Key 認証も許可（検証用途）
});
```

### 4.3 データスキーマ (`app/amplify/data/resource.ts`)

```typescript
import { a, defineData, type ClientSchema } from '@aws-amplify/backend';

const schema = a.schema({
  // ===========================================================================
  // Memory Types
  // ===========================================================================
  MemoryEvent: a.customType({
    id: a.id().required(),
    actorId: a.id().required(),
    sessionId: a.id().required(),
    role: a.enum(['USER', 'ASSISTANT', 'SYSTEM']),
    content: a.string().required(),
    timestamp: a.datetime(),
    metadata: a.json(),
  }),

  // ===========================================================================
  // Vector Types
  // ===========================================================================
  VectorResult: a.customType({
    id: a.id().required(),
    score: a.float().required(),
    content: a.string().required(),
    metadata: a.json(),
  }),

  // ===========================================================================
  // Graph Types
  // ===========================================================================
  GraphNode: a.customType({
    id: a.id().required(),
    labels: a.string().array().required(),
    properties: a.json().required(),
  }),

  GraphEdge: a.customType({
    id: a.id().required(),
    type: a.string().required(),
    sourceId: a.id().required(),
    targetId: a.id().required(),
    properties: a.json(),
  }),

  GraphQueryResult: a.customType({
    nodes: a.ref('GraphNode').array().required(),
    edges: a.ref('GraphEdge').array().required(),
  }),

  // ===========================================================================
  // Agent Types
  // ===========================================================================
  GeneratedImage: a.customType({
    base64: a.string().required(),
    seed: a.integer(),
  }),

  GeneratedVideo: a.customType({
    jobId: a.string().required(),
    status: a.string().required(),
    statusUrl: a.string(),
  }),

  AgentResponse: a.customType({
    success: a.boolean().required(),
    content: a.string(),
    images: a.ref('GeneratedImage').array(),
    videos: a.ref('GeneratedVideo').array(),
    error: a.string(),
  }),

  VoiceResponse: a.customType({
    sessionId: a.id().required(),
    transcript: a.string(),
    userText: a.string(),
    assistantText: a.string().required(),
    audio: a.string(),
    timestamp: a.datetime(),
  }),

  // ===========================================================================
  // Queries - Lambda Resolvers
  // ===========================================================================
  
  // Memory Query
  getMemoryEvents: a.query()
    .arguments({
      actorId: a.id().required(),
      sessionId: a.id(),
      limit: a.integer(),
    })
    .returns(a.ref('MemoryEvent').array())
    .handler(a.handler.function('memoryResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // Vector Search
  searchVectors: a.query()
    .arguments({
      query: a.string().required(),
      topK: a.integer(),
      filter: a.json(),
    })
    .returns(a.ref('VectorResult').array())
    .handler(a.handler.function('vectorResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // Graph Query
  getNode: a.query()
    .arguments({ id: a.id().required() })
    .returns(a.ref('GraphNode'))
    .handler(a.handler.function('graphResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  queryGraph: a.query()
    .arguments({
      cypher: a.string().required(),
      parameters: a.json(),
    })
    .returns(a.ref('GraphQueryResult'))
    .handler(a.handler.function('graphResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // ===========================================================================
  // Mutations - Lambda Resolvers
  // ===========================================================================
  
  // Memory Mutation
  createMemoryEvent: a.mutation()
    .arguments({
      actorId: a.id().required(),
      sessionId: a.id().required(),
      role: a.enum(['USER', 'ASSISTANT', 'SYSTEM']),
      content: a.string().required(),
      metadata: a.json(),
    })
    .returns(a.ref('MemoryEvent'))
    .handler(a.handler.function('memoryResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // Graph Mutations
  createNode: a.mutation()
    .arguments({
      labels: a.string().array().required(),
      properties: a.json().required(),
    })
    .returns(a.ref('GraphNode'))
    .handler(a.handler.function('graphResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // Agent - Multimodal
  invokeMultimodal: a.mutation()
    .arguments({
      message: a.string().required(),
      images: a.string().array(),
      videos: a.string().array(),
      sessionId: a.id(),
      actorId: a.id(),
    })
    .returns(a.ref('AgentResponse'))
    .handler(a.handler.function('agentResolver'))
    .authorization(allow => [allow.publicApiKey()]),

  // Agent - Voice
  sendVoiceText: a.mutation()
    .arguments({
      text: a.string().required(),
      voiceId: a.string(),
      language: a.string(),
      sessionId: a.id(),
      actorId: a.id(),
    })
    .returns(a.ref('VoiceResponse'))
    .handler(a.handler.function('agentResolver'))
    .authorization(allow => [allow.publicApiKey()]),
});

export type Schema = ClientSchema<typeof schema>;
export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'apiKey',
    apiKeyAuthorizationMode: {
      expiresInDays: 365,
    },
  },
});
```

### 4.4 Lambda Resolver (`app/amplify/functions/agent-resolver/handler.ts`)

```typescript
import type { AppSyncResolverHandler } from 'aws-lambda';

// StrandsAgents + AgentCore パッケージを使用
// boto3/cli/script/sh 直接処理禁止

interface MultimodalInput {
  message: string;
  images?: string[];
  videos?: string[];
  sessionId?: string;
  actorId?: string;
}

interface AgentResponse {
  success: boolean;
  content?: string;
  images?: { base64: string; seed?: number }[];
  videos?: { jobId: string; status: string; statusUrl?: string }[];
  error?: string;
}

export const handler: AppSyncResolverHandler<any, any> = async (event) => {
  const { fieldName, arguments: args } = event;

  switch (fieldName) {
    case 'invokeMultimodal':
      return handleMultimodal(args as MultimodalInput);
    case 'sendVoiceText':
      return handleVoiceText(args);
    default:
      throw new Error(`Unknown field: ${fieldName}`);
  }
};

async function handleMultimodal(input: MultimodalInput): Promise<AgentResponse> {
  // StrandsAgents を使用して AgentCore Runtime を呼び出し
  // AgentCore_Observability で追跡可能
  
  // TODO: 実装
  // - strands-agents パッケージを使用
  // - bedrock-agentcore パッケージを使用
  // - AgentCore Memory で会話履歴管理
  
  return {
    success: true,
    content: `Multimodal Agent Response: ${input.message}`,
  };
}

async function handleVoiceText(input: any): Promise<any> {
  // TODO: Nova Sonic 実装
  return {
    sessionId: input.sessionId || 'default',
    assistantText: `Voice Response: ${input.text}`,
    timestamp: new Date().toISOString(),
  };
}
```

### 4.5 フロントエンド設定 (`app/lib/amplify-config.ts`)

```typescript
'use client';

import { Amplify } from 'aws-amplify';
import outputs from '../amplify_outputs.json';

Amplify.configure(outputs);

export { generateClient } from 'aws-amplify/data';
```

### 4.6 GraphQL 使用例 (`app/page.tsx`)

```typescript
'use client';

import { generateClient } from 'aws-amplify/data';
import type { Schema } from './amplify/data/resource';

const client = generateClient<Schema>();

// Memory クエリ
const { data: events } = await client.queries.getMemoryEvents({
  actorId: 'user-123',
  sessionId: 'session-456',
});

// Multimodal Mutation
const { data: response } = await client.mutations.invokeMultimodal({
  message: 'この画像を説明してください',
  images: [base64Image],
});

// Voice Subscription (リアルタイム)
client.subscriptions.onVoiceResponse({ sessionId: 'session-456' }).subscribe({
  next: (data) => {
    console.log('Voice response:', data.assistantText);
  },
});
```

## 5. 移行タスク

| タスク ID | 内容 | 優先度 | 依存 |
|----------|------|--------|------|
| TASK-080 | Amplify Gen2 移行設計ドキュメント作成 | critical | - |
| TASK-081 | Amplify Gen2 プロジェクト初期化 (`app/amplify/`) | critical | TASK-080 |
| TASK-082 | Auth 設定 (`auth/resource.ts`) | high | TASK-081 |
| TASK-083 | Data スキーマ定義 (`data/resource.ts`) | critical | TASK-081 |
| TASK-084 | Memory Resolver Lambda 実装 | high | TASK-083 |
| TASK-085 | Vector Resolver Lambda 実装 | high | TASK-083 |
| TASK-086 | Graph Resolver Lambda 実装 | high | TASK-083 |
| TASK-087 | Agent Resolver Lambda 実装 (Multimodal/Voice) | high | TASK-083 |
| TASK-088 | Storage 設定 (`storage/resource.ts`) | medium | TASK-081 |
| TASK-089 | Backend 統合 (`backend.ts`) | critical | TASK-084~088 |
| TASK-090 | フロントエンド Amplify 統合 | high | TASK-089 |
| TASK-091 | 既存 API Gateway / CloudFront 削除 | medium | TASK-090 |
| TASK-092 | Amplify Hosting デプロイ | critical | TASK-090 |
| TASK-093 | E2E テスト実行・検証 | critical | TASK-092 |

## 6. コマンド

```bash
# Amplify Gen2 初期化（app/ ディレクトリ内）
cd app
npm create amplify@latest

# Sandbox 起動（ローカル開発）
npx ampx sandbox

# 本番デプロイ
npx ampx pipeline-deploy --branch main

# GraphQL スキーマ検証
npx ampx generate graphql-client-code
```

## 7. 環境変数

```bash
# .env.local (ローカル開発)
NEXT_PUBLIC_AMPLIFY_BACKEND=sandbox

# .env.production (本番)
NEXT_PUBLIC_AMPLIFY_BACKEND=production
```

`amplify_outputs.json` は Amplify が自動生成するため、環境変数でのハードコードは不要。

## 8. 検証項目

- [ ] `npx ampx sandbox` でローカル開発環境起動
- [ ] GraphQL クエリ/ミューテーション正常動作
- [ ] Subscription リアルタイム通信
- [ ] CORS エラーなし
- [ ] CloudTrail / X-Ray 追跡可能
- [ ] Amplify Hosting で本番デプロイ
- [ ] モック/フォールバックなしで本番接続
- [ ] Branch デプロイで環境分離
