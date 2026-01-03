# rd-knowledge-sample アーキテクチャサマリー

## プロジェクト概要

AWS Nova シリーズ技術検証プロジェクト。
AgentCore + StrandsAgents + Bedrock API を活用した AI エージェントシステム。

## 設計プロセス

```
RDRA要件分析 → DDD+イベントストーミング → クリーンアーキテクチャ
     │                  │                        │
     ▼                  ▼                        ▼
  01-RDRA.md      02-DDD-DOMAIN.md      03-CLEAN-ARCHITECTURE.md
                  03-EVENT-STORMING.md  04-TWELVE-FACTOR.md
                                                 │
                                                 ▼
                                     FSD+アトミックデザイン → TDD
                                            │               │
                                            ▼               ▼
                                    05-FSD-ATOMIC.md  06-TDD-STRATEGY.md
```

## ディレクトリ構成

```
rd-knowledge-sample/
├── docs/design/                    # 設計ドキュメント
│   ├── 00-ARCHITECTURE-SUMMARY.md  # 本ファイル
│   ├── 01-RDRA-REQUIREMENTS.md     # 要件分析
│   ├── 02-DDD-DOMAIN-MODEL.md      # ドメインモデル
│   ├── 03-EVENT-STORMING.md        # イベントストーミング
│   ├── 04-CLEAN-ARCHITECTURE.md    # クリーンアーキテクチャ
│   ├── 04-TWELVE-FACTOR.md         # 12 Factor 原則
│   ├── 05-FSD-ATOMIC-DESIGN.md     # フロントエンド設計
│   ├── 06-TDD-STRATEGY.md          # TDD 戦略
│   └── 07-MICROSERVICES-IMPL.md    # 実装ガイド
│
├── services/                       # マイクロサービス
│   ├── memory/                     # Memory サービス
│   │   ├── domain/                 # ドメイン層
│   │   │   ├── entities/           # エンティティ・集約
│   │   │   ├── events/             # ドメインイベント
│   │   │   ├── value_objects/      # 値オブジェクト
│   │   │   └── repositories/       # リポジトリIF
│   │   ├── application/            # アプリケーション層
│   │   │   ├── commands/           # CQRS コマンド
│   │   │   ├── queries/            # CQRS クエリ
│   │   │   └── handlers/           # ハンドラ
│   │   └── infrastructure/         # インフラ層
│   │       └── repositories/       # リポジトリ実装
│   ├── search/                     # Search サービス
│   └── agent/                      # Agent サービス
│
├── shared/                         # 共有コンポーネント
│   ├── domain/
│   │   ├── events/                 # 共通イベント
│   │   └── value_objects/          # 共通値オブジェクト
│   ├── infrastructure/
│   │   ├── event_bus/              # イベントバス
│   │   └── observability/          # トレーシング
│   └── api/                        # API 共通処理
│
├── app/                            # フロントエンド (Next.js)
│   ├── (features)/                 # FSD 機能スライス
│   │   ├── memory/                 # Memory 機能
│   │   ├── multimodal/             # Multimodal 機能
│   │   └── voice/                  # Voice 機能
│   ├── shared/ui/                  # Atomic Design
│   │   ├── atoms/
│   │   ├── molecules/
│   │   ├── organisms/
│   │   └── templates/
│   ├── entities/                   # ビジネスエンティティ
│   ├── widgets/                    # 複合コンポーネント
│   └── amplify/                    # Amplify Gen2 バックエンド
│       ├── data/resource.ts        # AppSync スキーマ
│       ├── functions/              # Lambda リゾルバ
│       └── backend.ts              # バックエンド定義
│
├── tests/                          # テスト
│   ├── unit/domain/                # ユニットテスト (27件)
│   ├── integration/                # 統合テスト (7件)
│   └── e2e/                        # E2E テスト
│
└── infra/                          # CDK インフラ (レガシー)
```

## 技術スタック

### バックエンド

| コンポーネント | 技術 |
|---------------|------|
| API | AppSync (GraphQL) |
| Compute | Lambda (Node.js 20) |
| Memory | AgentCore Memory / S3 |
| AI Models | Bedrock Nova Series |
| Agent Framework | StrandsAgents |

### フロントエンド

| コンポーネント | 技術 |
|---------------|------|
| Framework | Next.js 14 (App Router) |
| State Management | Apollo Client |
| UI Design | Atomic Design + FSD |
| Hosting | Amplify Hosting |

### インフラ

| コンポーネント | 技術 |
|---------------|------|
| IaC | Amplify Gen2 / CDK |
| CI/CD | Amplify CI/CD |
| Monitoring | CloudWatch |
| Tracing | CloudTrail |

## 境界付けられたコンテキスト

```
┌────────────────────────────────────────────────────────────────┐
│                    Knowledge Sample System                      │
├────────────────────┬────────────────────┬─────────────────────┤
│  Memory Context    │  Search Context    │  Agent Context       │
│                    │                    │                      │
│  - Session         │  - Vector          │  - Multimodal Agent  │
│  - MemoryEvent     │  - Embedding       │  - Voice Agent       │
│  - Actor           │  - Document        │  - Tool              │
│                    │                    │                      │
│  AgentCore Memory  │  S3 Vector Store   │  Bedrock Nova        │
└────────────────────┴────────────────────┴─────────────────────┘
```

## テスト状況

| カテゴリ | 件数 | 状態 |
|----------|------|------|
| Unit Tests | 27 | ✅ Pass |
| Integration Tests | 7 | ✅ Pass |
| E2E Tests | - | ⏳ 実装中 |

## 次のステップ

1. ✅ RDRA 要件分析
2. ✅ DDD + Event Storming
3. ✅ Clean Architecture + CQRS + ES
4. ✅ 12 Factor App + 12 Agent Factor
5. ✅ FSD + Atomic Design
6. ✅ TDD テスト戦略
7. ⏳ マイクロサービス実装
   - [ ] AgentCore Memory 統合
   - [ ] Bedrock Nova 統合
   - [ ] AppSync デプロイ
8. ⏳ フロントエンド実装
   - [ ] テストダッシュボード UI
   - [ ] Apollo Client 統合
9. ⏳ E2E テスト

---

**作成日**: 2026-01-03
**更新日**: 2026-01-03
