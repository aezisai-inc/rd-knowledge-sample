# マイクロサービス実装ガイド

## 概要

12 Factor App + 12 Agent Factor 原則に基づくマイクロサービス実装。
AgentCore + StrandsAgents + Bedrock API を活用。

## サービス構成

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (AppSync)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ Memory Service │           │ Search Service │           │ Agent Service  │
│   (Session)    │           │   (Vector)     │           │ (Multimodal)   │
└───────────────┘           └───────────────┘           └───────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│ AgentCore     │           │ S3 Vector     │           │ Bedrock Nova  │
│ Memory        │           │ Store         │           │ Models        │
└───────────────┘           └───────────────┘           └───────────────┘
```

## 実装済みコンポーネント

### Memory Service

```
services/memory/
├── domain/
│   ├── entities/
│   │   └── session.py       # Session 集約ルート
│   ├── events/              # ドメインイベント
│   ├── value_objects/       # 値オブジェクト
│   └── repositories/        # リポジトリインターフェース
├── application/
│   ├── commands/           # CQRS コマンド
│   ├── queries/            # CQRS クエリ
│   └── handlers/           # コマンド/クエリハンドラ
└── infrastructure/
    └── repositories/       # リポジトリ実装
```

### Shared Domain

```
shared/
├── domain/
│   ├── events/             # 共通ドメインイベント
│   └── value_objects/
│       └── entity_id.py    # ID 値オブジェクト
├── infrastructure/
│   ├── event_bus/          # イベントバス
│   └── observability/      # トレーシング
└── api/                    # API 共通処理
```

## 12 Factor App 対応状況

| Factor | 実装状況 | 詳細 |
|--------|----------|------|
| I. Codebase | ✅ | Git モノレポ |
| II. Dependencies | ✅ | pyproject.toml |
| III. Config | ✅ | 環境変数 |
| IV. Backing Services | ✅ | DI / Protocol |
| V. Build, Release, Run | ⏳ | Amplify CI/CD |
| VI. Processes | ✅ | ステートレス Lambda |
| VII. Port Binding | ✅ | AppSync エンドポイント |
| VIII. Concurrency | ✅ | Lambda スケーリング |
| IX. Disposability | ✅ | Lambda 高速起動 |
| X. Dev/Prod Parity | ⏳ | Amplify Sandbox |
| XI. Logs | ✅ | CloudWatch |
| XII. Admin Processes | ⏳ | 管理タスク |

## 12 Agent Factor 対応状況

| Factor | 実装状況 | 詳細 |
|--------|----------|------|
| I. Model Independence | ✅ | ModelId 値オブジェクト |
| II. Tool Abstraction | ⏳ | StrandsAgents Tools |
| III. Memory Hierarchy | ✅ | AgentCore Memory |
| IV. Context Management | ✅ | Session 集約 |
| V. Observability | ✅ | CloudTrail 対応設計 |
| VI. Graceful Degradation | ⏳ | フォールバック機構 |
| VII. Security First | ✅ | IAM ロール分離 |
| VIII. Cost Awareness | ✅ | S3Vector 優先 |
| IX. Human-in-the-Loop | ⏳ | 承認フロー |
| X. Evaluation Driven | ⏳ | テスト戦略 |
| XI. Multi-Agent Coordination | ⏳ | A2A 対応 |
| XII. Ethical Constraints | ⏳ | ガードレール |

## デプロイ構成

### Amplify Gen2

```typescript
// amplify/backend.ts
const backend = defineBackend({
  auth,
  data,
  memoryResolver,
  searchResolver,
  agentResolver,
});
```

### Lambda Resolver 構成

```typescript
// amplify/functions/memory-resolver/resource.ts
export const memoryResolver = defineFunction({
  name: 'memoryResolver',
  entry: './handler.ts',
  runtime: 20,
  environment: {
    AGENTCORE_MEMORY_ID: process.env.AGENTCORE_MEMORY_ID!,
    OUTPUT_BUCKET: process.env.OUTPUT_BUCKET!,
  },
});
```

## 次のステップ

1. **AgentCore Memory 統合**
   - S3 バックエンド設定
   - Session 永続化実装

2. **Bedrock API 統合**
   - Nova Vision 画像処理
   - Nova Sonic 音声処理
   - Nova Reel 動画生成

3. **フロントエンド実装**
   - FSD + Atomic Design
   - Apollo Client 統合
   - テストダッシュボード

4. **E2E テスト**
   - GraphQL API テスト
   - Playwright UI テスト

---

**更新日**: 2026-01-03
