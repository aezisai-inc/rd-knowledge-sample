# rd-knowledge-sample アーキテクチャ設計書

## 設計プロセスフロー

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           設計プロセス                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ① RDRA (要件分析)                                                          │
│     ├─ システムコンテキスト図                                                 │
│     ├─ 業務フロー                                                           │
│     ├─ ユースケース                                                          │
│     └─ 情報モデル                                                           │
│              │                                                              │
│              ▼                                                              │
│  ② DDD + Event Storming (ドメイン発見)                                       │
│     ├─ ドメインイベント                                                      │
│     ├─ コマンド / ポリシー                                                   │
│     ├─ 集約 / エンティティ                                                   │
│     └─ 境界付けられたコンテキスト                                              │
│              │                                                              │
│              ▼                                                              │
│  ③ Clean Architecture + Event Sourcing + CQRS (バックエンド)                  │
│     ├─ Entities (ドメインモデル)                                             │
│     ├─ Use Cases (アプリケーション層)                                         │
│     ├─ Interface Adapters (アダプター層)                                      │
│     └─ Frameworks & Drivers (インフラ層)                                     │
│              │                                                              │
│              ▼                                                              │
│  ④ 12 Factor App + 12 Agent Factor (マイクロサービス原則)                      │
│     ├─ サービス分割                                                          │
│     ├─ 設定の外部化                                                          │
│     ├─ ステートレス設計                                                      │
│     └─ エージェント固有原則                                                   │
│              │                                                              │
│              ▼                                                              │
│  ⑤ FSD + Atomic Design (フロントエンド)                                       │
│     ├─ Feature Slices                                                       │
│     ├─ Atomic Components                                                    │
│     └─ Shared UI Library                                                    │
│              │                                                              │
│              ▼                                                              │
│  ⑥ TDD (テスト駆動開発)                                                       │
│     ├─ Unit Tests (Red-Green-Refactor)                                      │
│     ├─ Integration Tests                                                    │
│     └─ E2E Tests                                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. RDRA 要件分析

### 1.1 システムコンテキスト図

```
                              ┌─────────────────┐
                              │   開発者/QA     │
                              │  (ユーザー)      │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │   Memory      │  │  Multimodal   │  │    Voice      │
           │   Tester      │  │    Agent      │  │   Dialogue    │
           └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   rd-knowledge-sample   │
                         │   (統合テストプラット    │
                         │    フォーム)             │
                         └────────────┬────────────┘
                                      │
           ┌──────────────┬───────────┼───────────┬──────────────┐
           │              │           │           │              │
           ▼              ▼           ▼           ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
    │ AgentCore │  │ S3 Vector │  │  Neo4j    │  │  Bedrock  │  │  Polly/   │
    │  Memory   │  │           │  │  AuraDB   │  │  Models   │  │Transcribe │
    └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

### 1.2 業務フロー

| フロー ID | フロー名 | アクター | 概要 |
|-----------|---------|---------|------|
| BF-001 | Memory テスト実行 | 開発者 | AgentCore Memory の CRUD 操作を検証 |
| BF-002 | Vector 検索テスト | 開発者 | S3 Vector / Bedrock KB の検索精度を検証 |
| BF-003 | Graph クエリテスト | 開発者 | Neo4j のグラフ操作を検証 |
| BF-004 | Multimodal Agent テスト | QA | 画像/動画の理解・生成を検証 |
| BF-005 | Voice Dialogue テスト | QA | 音声対話の品質を検証 |
| BF-006 | 比較レポート生成 | 開発者 | 複数サービスの比較レポート出力 |

### 1.3 ユースケース

```yaml
UC-001:
  name: セッション開始
  actor: ユーザー
  preconditions: システムにアクセス可能
  main_flow:
    1. ユーザーがテストタイプを選択
    2. システムがセッションIDを発行
    3. AgentCore Memory にセッション作成
  postconditions: セッションが有効化

UC-002:
  name: Memory イベント記録
  actor: システム
  preconditions: 有効なセッション
  main_flow:
    1. ユーザー/アシスタントメッセージ受信
    2. AgentCore Memory にイベント追加
    3. 記録完了を通知
  postconditions: イベントが永続化

UC-003:
  name: Vector 検索実行
  actor: ユーザー
  preconditions: ベクトルストアが初期化済み
  main_flow:
    1. クエリテキスト入力
    2. 埋め込みベクトル生成
    3. 類似度検索実行
    4. 結果をランキング表示
  postconditions: 検索結果が表示

UC-004:
  name: Multimodal Agent 呼び出し
  actor: ユーザー
  preconditions: 有効なセッション
  main_flow:
    1. テキスト/画像/動画を入力
    2. StrandsAgents が処理
    3. Nova モデルで理解/生成
    4. 結果を返却
  postconditions: 応答が表示

UC-005:
  name: Voice 対話処理
  actor: ユーザー
  preconditions: マイクアクセス許可
  main_flow:
    1. 音声入力開始
    2. Transcribe で STT
    3. Agent が応答生成
    4. Polly で TTS
    5. 音声再生
  postconditions: 対話完了
```

### 1.4 情報モデル

```yaml
entities:
  Session:
    attributes:
      - id: UUID
      - actorId: UUID
      - type: Enum[Memory, Multimodal, Voice]
      - createdAt: DateTime
      - updatedAt: DateTime
      - metadata: JSON

  MemoryEvent:
    attributes:
      - id: UUID
      - sessionId: UUID
      - actorId: UUID
      - role: Enum[USER, ASSISTANT, SYSTEM]
      - content: String
      - timestamp: DateTime
      - metadata: JSON

  VectorDocument:
    attributes:
      - id: UUID
      - content: String
      - embedding: Float[]
      - metadata: JSON
      - createdAt: DateTime

  GraphNode:
    attributes:
      - id: UUID
      - labels: String[]
      - properties: JSON

  GraphEdge:
    attributes:
      - id: UUID
      - type: String
      - sourceId: UUID
      - targetId: UUID
      - properties: JSON

  AgentResponse:
    attributes:
      - id: UUID
      - sessionId: UUID
      - success: Boolean
      - content: String
      - images: Image[]
      - videos: Video[]
      - audio: Binary
      - error: String
```

---

## 2. DDD + Event Storming

### 2.1 ドメインイベント (オレンジ付箋)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Timeline →                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Session      │   │ Memory       │   │ Memory       │   │ Session      │ │
│  │ Started      │──▶│ Event        │──▶│ Retrieved    │──▶│ Ended        │ │
│  │              │   │ Created      │   │              │   │              │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ Vector       │   │ Vectors      │   │ Search       │                    │
│  │ Indexed      │──▶│ Searched     │──▶│ Results      │                    │
│  │              │   │              │   │ Returned     │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ Node         │   │ Edge         │   │ Graph        │                    │
│  │ Created      │──▶│ Created      │──▶│ Queried      │                    │
│  │              │   │              │   │              │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │ Agent        │   │ Image        │   │ Video        │   │ Agent        │ │
│  │ Invoked      │──▶│ Generated    │──▶│ Generated    │──▶│ Completed    │ │
│  │              │   │              │   │              │   │              │ │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘ │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ Voice        │   │ Speech       │   │ Voice        │                    │
│  │ Input        │──▶│ Recognized   │──▶│ Response     │                    │
│  │ Received     │   │              │   │ Synthesized  │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 コマンド (青付箋) & ポリシー (紫付箋)

```yaml
commands:
  # Memory Context
  - StartSession
  - CreateMemoryEvent
  - RetrieveMemory
  - EndSession
  - DeleteSession

  # Vector Context
  - IndexDocument
  - SearchVectors
  - DeleteDocument

  # Graph Context
  - CreateNode
  - UpdateNode
  - DeleteNode
  - CreateEdge
  - DeleteEdge
  - QueryGraph

  # Agent Context
  - InvokeMultimodalAgent
  - GenerateImage
  - GenerateVideo
  - ProcessVoiceInput
  - SynthesizeVoice

policies:
  - WhenSessionStarted_ThenCreateMemory
  - WhenMessageReceived_ThenRecordEvent
  - WhenQueryReceived_ThenSearchAndRespond
  - WhenImageRequested_ThenGenerateWithNova
  - WhenVoiceReceived_ThenTranscribeAndRespond
```

### 2.3 集約 (黄色付箋)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Bounded Contexts                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Memory Context                                   │   │
│  │  ┌─────────────────┐                                                │   │
│  │  │   <<Aggregate>> │                                                │   │
│  │  │     Session     │                                                │   │
│  │  │  ┌───────────┐  │                                                │   │
│  │  │  │MemoryEvent│  │  (Root Entity + Events)                        │   │
│  │  │  └───────────┘  │                                                │   │
│  │  └─────────────────┘                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Vector Context                                   │   │
│  │  ┌─────────────────┐                                                │   │
│  │  │   <<Aggregate>> │                                                │   │
│  │  │  VectorStore    │                                                │   │
│  │  │  ┌───────────┐  │                                                │   │
│  │  │  │ Document  │  │  (Root Entity + Documents)                     │   │
│  │  │  └───────────┘  │                                                │   │
│  │  └─────────────────┘                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Graph Context                                    │   │
│  │  ┌─────────────────┐                                                │   │
│  │  │   <<Aggregate>> │                                                │   │
│  │  │   GraphStore    │                                                │   │
│  │  │  ┌───────────┐  │                                                │   │
│  │  │  │   Node    │──│──┐                                             │   │
│  │  │  └───────────┘  │  │                                             │   │
│  │  │  ┌───────────┐  │  │                                             │   │
│  │  │  │   Edge    │◀─│──┘ (Nodes + Edges)                             │   │
│  │  │  └───────────┘  │                                                │   │
│  │  └─────────────────┘                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Agent Context                                    │   │
│  │  ┌─────────────────┐         ┌─────────────────┐                    │   │
│  │  │   <<Aggregate>> │         │   <<Aggregate>> │                    │   │
│  │  │ MultimodalAgent │         │   VoiceAgent    │                    │   │
│  │  │  ┌───────────┐  │         │  ┌───────────┐  │                    │   │
│  │  │  │  Response │  │         │  │ Dialogue  │  │                    │   │
│  │  │  └───────────┘  │         │  └───────────┘  │                    │   │
│  │  └─────────────────┘         └─────────────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 コンテキストマップ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Context Map                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌──────────────────┐                                     │
│                    │   API Gateway    │                                     │
│                    │   (AppSync)      │                                     │
│                    └────────┬─────────┘                                     │
│                             │                                               │
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   Memory    │     │   Search    │     │   Agent     │                   │
│  │   Context   │     │   Context   │     │   Context   │                   │
│  │             │     │             │     │             │                   │
│  │ [U] Session │     │[U] Vector   │     │[U] Multi    │                   │
│  │     Events  │     │    Graph    │     │    Voice    │                   │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                   │
│         │                   │                   │                           │
│         │    Shared Kernel  │                   │                           │
│         └─────────┬─────────┘                   │                           │
│                   │                             │                           │
│                   ▼                             │                           │
│            ┌─────────────┐                      │                           │
│            │   Shared    │◀─────────────────────┘                           │
│            │   Domain    │                                                  │
│            │   Events    │                                                  │
│            └─────────────┘                                                  │
│                   │                                                         │
│    Anti-Corruption Layer                                                    │
│         ┌─────────┴─────────┐                                               │
│         ▼                   ▼                                               │
│  ┌─────────────┐     ┌─────────────┐                                       │
│  │  AgentCore  │     │   Bedrock   │                                       │
│  │  (External) │     │  (External) │                                       │
│  └─────────────┘     └─────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Relationship Types:
  [U] = Upstream
  [D] = Downstream
  SK  = Shared Kernel
  ACL = Anti-Corruption Layer
```

---

## 3. Clean Architecture + Event Sourcing + CQRS

### 3.1 レイヤー構造

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Clean Architecture Layers                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    Frameworks & Drivers (外側)                         │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │ │
│  │  │AppSync  │  │ Lambda  │  │AgentCore│  │ Neo4j   │  │ S3      │     │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│  │  │                   Interface Adapters                              │ │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐              │ │ │
│  │  │  │GraphQL  │  │ REST    │  │Presenter│  │Repository│             │ │ │
│  │  │  │Resolver │  │Handler  │  │         │  │ Impl    │              │ │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘              │ │ │
│  │  │  ┌───────────────────────────────────────────────────────────────┐ │ │ │
│  │  │  │                   Application (Use Cases)                     │ │ │ │
│  │  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐     │ │ │ │
│  │  │  │  │ Command       │  │ Query         │  │ Event         │     │ │ │ │
│  │  │  │  │ Handlers      │  │ Handlers      │  │ Handlers      │     │ │ │ │
│  │  │  │  │               │  │               │  │               │     │ │ │ │
│  │  │  │  │ CreateSession │  │ GetSession    │  │ OnSessionStart│     │ │ │ │
│  │  │  │  │ CreateEvent   │  │ GetEvents     │  │ OnEventCreated│     │ │ │ │
│  │  │  │  │ InvokeAgent   │  │ SearchVectors │  │ OnAgentInvoked│     │ │ │ │
│  │  │  │  └───────────────┘  └───────────────┘  └───────────────┘     │ │ │ │
│  │  │  │  ┌───────────────────────────────────────────────────────────┐ │ │ │ │
│  │  │  │  │                  Entities (Domain)                        │ │ │ │ │
│  │  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │ │ │ │ │
│  │  │  │  │  │ Session │  │Document │  │  Node   │  │  Agent  │      │ │ │ │ │
│  │  │  │  │  │MemEvent │  │Embedding│  │  Edge   │  │Response │      │ │ │ │ │
│  │  │  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │ │ │ │ │
│  │  │  │  │                                                           │ │ │ │ │
│  │  │  │  │  Domain Events:                                           │ │ │ │ │
│  │  │  │  │  ├─ SessionStarted                                        │ │ │ │ │
│  │  │  │  │  ├─ MemoryEventCreated                                    │ │ │ │ │
│  │  │  │  │  ├─ VectorIndexed                                         │ │ │ │ │
│  │  │  │  │  ├─ GraphNodeCreated                                      │ │ │ │ │
│  │  │  │  │  ├─ AgentInvoked                                          │ │ │ │ │
│  │  │  │  │  └─ VoiceProcessed                                        │ │ │ │ │
│  │  │  │  └───────────────────────────────────────────────────────────┘ │ │ │ │
│  │  │  └───────────────────────────────────────────────────────────────┘ │ │ │
│  │  └───────────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 CQRS パターン

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CQRS Architecture                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        ┌───────────────┐                                    │
│                        │   AppSync     │                                    │
│                        │  (GraphQL)    │                                    │
│                        └───────┬───────┘                                    │
│                                │                                            │
│              ┌─────────────────┴─────────────────┐                          │
│              │                                   │                          │
│              ▼                                   ▼                          │
│     ┌─────────────────┐               ┌─────────────────┐                  │
│     │    Command      │               │     Query       │                  │
│     │     Side        │               │      Side       │                  │
│     └────────┬────────┘               └────────┬────────┘                  │
│              │                                  │                           │
│              ▼                                  ▼                           │
│     ┌─────────────────┐               ┌─────────────────┐                  │
│     │ Command Handler │               │  Query Handler  │                  │
│     │                 │               │                 │                  │
│     │ - Validation    │               │ - Read Model    │                  │
│     │ - Business Rule │               │ - Projection    │                  │
│     │ - Persist Event │               │ - Caching       │                  │
│     └────────┬────────┘               └────────┬────────┘                  │
│              │                                  │                           │
│              ▼                                  ▼                           │
│     ┌─────────────────┐               ┌─────────────────┐                  │
│     │  Event Store    │               │   Read Store    │                  │
│     │                 │──────────────▶│                 │                  │
│     │ - Event Stream  │   Projection  │ - DynamoDB      │                  │
│     │ - AgentCore Mem │               │ - S3 Vectors    │                  │
│     └─────────────────┘               └─────────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Event Sourcing フロー

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Event Sourcing Flow                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Command → 2. Validate → 3. Create Event → 4. Store → 5. Project        │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────┐│
│  │CreateMem │───▶│Aggregate │───▶│MemEvent  │───▶│AgentCore │───▶│ReadDB ││
│  │Event     │    │ Rules    │    │ Created  │    │ Memory   │    │Update ││
│  │(Command) │    │          │    │ (Event)  │    │ (Store)  │    │       ││
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └───────┘│
│                                                                             │
│  Event Stream Example:                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ stream_id: session-123                                               │  │
│  │ ├─ [0] SessionStarted    { actorId: "user-1", type: "memory" }       │  │
│  │ ├─ [1] MemoryEventCreated { role: "USER", content: "Hello" }         │  │
│  │ ├─ [2] MemoryEventCreated { role: "ASSISTANT", content: "Hi" }       │  │
│  │ ├─ [3] MemoryRetrieved   { count: 2 }                                │  │
│  │ └─ [4] SessionEnded      { duration: 300000 }                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 12 Factor App + 12 Agent Factor

### 4.1 12 Factor App 適用

| Factor | 原則 | 本プロジェクトでの適用 |
|--------|------|----------------------|
| I. Codebase | 1つのコードベース、複数デプロイ | Git monorepo + branch per env |
| II. Dependencies | 依存関係を明示的に宣言 | package.json, requirements.txt |
| III. Config | 環境設定を環境変数に | Amplify env, SSM Parameter |
| IV. Backing Services | バッキングサービスをアタッチ | AgentCore, S3, Neo4j を疎結合 |
| V. Build, Release, Run | ビルド・リリース・実行を厳密に分離 | Amplify CI/CD Pipeline |
| VI. Processes | ステートレスプロセスとして実行 | Lambda + AppSync |
| VII. Port Binding | ポートバインディングでサービス公開 | AppSync Endpoint |
| VIII. Concurrency | プロセスモデルでスケールアウト | Lambda 並列実行 |
| IX. Disposability | 迅速な起動・グレースフルシャットダウン | Lambda Cold Start 最適化 |
| X. Dev/Prod Parity | 開発・本番の一貫性 | Amplify Sandbox/Prod |
| XI. Logs | ログをイベントストリームとして扱う | CloudWatch Logs |
| XII. Admin Processes | 管理タスクを1回限りのプロセスで | Amplify Functions |

### 4.2 12 Agent Factor 適用

| Factor | 原則 | 本プロジェクトでの適用 |
|--------|------|----------------------|
| I. Agent Identity | エージェントの一意識別 | AgentCore Agent ID |
| II. Model Abstraction | モデルの抽象化 | StrandsAgents Model Binding |
| III. Tool Encapsulation | ツールのカプセル化 | Tools as Protocol |
| IV. Memory Externalization | メモリの外部化 | AgentCore Memory |
| V. Prompt as Config | プロンプトを設定として管理 | YAML/JSON 設定ファイル |
| VI. Session Management | セッション管理 | Session Aggregate |
| VII. Observability | 可観測性 | X-Ray + CloudTrail |
| VIII. Graceful Degradation | 優雅な劣化 | Fallback Responses |
| IX. Human-in-Loop | 人間介入ポイント | Approval Workflows |
| X. Idempotency | 冪等性 | Event ID による重複排除 |
| XI. Rate Limiting | レート制限 | API Gateway Throttling |
| XII. Cost Awareness | コスト意識 | Token/Request 課金モニタリング |

### 4.3 マイクロサービス構成

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Microservices Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Gateway (AppSync)                        │   │
│  │                    GraphQL Unified Endpoint                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│         ┌────────────────────────────┼────────────────────────────┐        │
│         │                            │                            │        │
│         ▼                            ▼                            ▼        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │
│  │  Memory Service │    │  Search Service │    │  Agent Service  │       │
│  │                 │    │                 │    │                 │       │
│  │  - Session      │    │  - Vector       │    │  - Multimodal   │       │
│  │  - Events       │    │  - Graph        │    │  - Voice        │       │
│  │  - History      │    │  - Semantic     │    │  - Reasoning    │       │
│  │                 │    │                 │    │                 │       │
│  │  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │       │
│  │  │Lambda     │  │    │  │Lambda     │  │    │  │Lambda     │  │       │
│  │  │Resolver   │  │    │  │Resolver   │  │    │  │Resolver   │  │       │
│  │  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │       │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘       │
│           │                      │                      │                 │
│           ▼                      ▼                      ▼                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │
│  │  AgentCore      │    │  S3 Vectors     │    │  Bedrock        │       │
│  │  Memory         │    │  Neo4j AuraDB   │    │  Nova Models    │       │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘       │
│                                                                             │
│  Event Bus (Domain Events):                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  EventBridge / AppSync Subscriptions                                 │   │
│  │  - SessionStarted → Memory Service                                   │   │
│  │  - MemoryEventCreated → Search Service (Indexing)                    │   │
│  │  - AgentInvoked → Observability                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. FSD + Atomic Design (フロントエンド)

### 5.1 Feature-Sliced Design 構造

```
app/                                    # Next.js App Router
├── (features)/                         # Feature Slices
│   ├── memory/                         # Memory Test Feature
│   │   ├── ui/                         # Feature-specific UI
│   │   │   ├── MemoryTester.tsx
│   │   │   ├── SessionList.tsx
│   │   │   └── EventTimeline.tsx
│   │   ├── model/                      # Feature State/Logic
│   │   │   ├── useMemorySession.ts
│   │   │   └── memoryStore.ts
│   │   ├── api/                        # Feature API calls
│   │   │   └── memoryApi.ts
│   │   └── lib/                        # Feature utilities
│   │       └── memoryHelpers.ts
│   │
│   ├── multimodal/                     # Multimodal Agent Feature
│   │   ├── ui/
│   │   │   ├── MultimodalTester.tsx
│   │   │   ├── ImageUploader.tsx
│   │   │   ├── ImageGallery.tsx
│   │   │   └── VideoPlayer.tsx
│   │   ├── model/
│   │   │   ├── useMultimodalAgent.ts
│   │   │   └── multimodalStore.ts
│   │   ├── api/
│   │   │   └── agentApi.ts
│   │   └── lib/
│   │       └── mediaHelpers.ts
│   │
│   └── voice/                          # Voice Dialogue Feature
│       ├── ui/
│       │   ├── VoiceDialogue.tsx
│       │   ├── VoiceRecorder.tsx
│       │   ├── WaveformVisualizer.tsx
│       │   └── TranscriptDisplay.tsx
│       ├── model/
│       │   ├── useVoiceSession.ts
│       │   └── voiceStore.ts
│       ├── api/
│       │   └── voiceApi.ts
│       └── lib/
│           └── audioHelpers.ts
│
├── shared/                             # Shared Layer
│   ├── ui/                             # Atomic Design Components
│   │   ├── atoms/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Icon.tsx
│   │   │   └── Spinner.tsx
│   │   ├── molecules/
│   │   │   ├── FormField.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Alert.tsx
│   │   │   └── Dropdown.tsx
│   │   ├── organisms/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── TabNavigation.tsx
│   │   └── templates/
│   │       ├── DashboardLayout.tsx
│   │       └── TesterLayout.tsx
│   │
│   ├── api/                            # Shared API Client
│   │   ├── amplifyClient.ts
│   │   └── graphqlOperations.ts
│   │
│   ├── lib/                            # Shared Utilities
│   │   ├── cn.ts                       # classnames helper
│   │   ├── date.ts                     # date formatting
│   │   └── validation.ts               # form validation
│   │
│   └── config/                         # Shared Configuration
│       ├── constants.ts
│       └── env.ts
│
├── entities/                           # Domain Entities (Types)
│   ├── session/
│   │   └── types.ts
│   ├── memory/
│   │   └── types.ts
│   ├── agent/
│   │   └── types.ts
│   └── graph/
│       └── types.ts
│
├── widgets/                            # Composed UI Widgets
│   ├── TestDashboard/
│   │   └── TestDashboard.tsx
│   ├── ResultsComparison/
│   │   └── ResultsComparison.tsx
│   └── TestHistory/
│       └── TestHistory.tsx
│
└── app/                                # Next.js Pages
    ├── layout.tsx
    ├── page.tsx
    └── (routes)/
        ├── memory/
        │   └── page.tsx
        ├── multimodal/
        │   └── page.tsx
        └── voice/
            └── page.tsx
```

### 5.2 Atomic Design コンポーネント階層

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Atomic Design Hierarchy                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Pages (Next.js Routes)                                                     │
│  └─ /memory, /multimodal, /voice                                           │
│     │                                                                       │
│     ▼                                                                       │
│  Templates (Layout Structures)                                              │
│  └─ DashboardLayout, TesterLayout                                          │
│     │                                                                       │
│     ▼                                                                       │
│  Organisms (Complex UI Sections)                                            │
│  └─ Header, Sidebar, TabNavigation, Modal                                  │
│     │                                                                       │
│     ▼                                                                       │
│  Molecules (UI Combinations)                                                │
│  └─ FormField, Card, Alert, Dropdown                                       │
│     │                                                                       │
│     ▼                                                                       │
│  Atoms (Base Elements)                                                      │
│  └─ Button, Input, Badge, Icon, Spinner                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. TDD テスト戦略

### 6.1 テストピラミッド

```
                    ┌───────────┐
                    │   E2E     │  ← Playwright / Cypress
                    │   Tests   │     (少数、高コスト)
                    └─────┬─────┘
                          │
                    ┌─────┴─────┐
                    │Integration│  ← pytest / jest
                    │  Tests    │     (中程度)
                    └─────┬─────┘
                          │
              ┌───────────┴───────────┐
              │      Unit Tests       │  ← pytest / jest / vitest
              │                       │     (多数、低コスト)
              └───────────────────────┘
```

### 6.2 TDD Red-Green-Refactor サイクル

```python
# Example: Memory Event Creation (Python)

# 1. RED: Write failing test first
def test_create_memory_event_should_return_event_with_id():
    # Arrange
    session_id = "session-123"
    content = "Hello, World!"
    role = "USER"
    
    # Act
    event = memory_service.create_event(session_id, role, content)
    
    # Assert
    assert event.id is not None
    assert event.session_id == session_id
    assert event.content == content
    assert event.role == role

# 2. GREEN: Implement minimal code to pass
class MemoryService:
    def create_event(self, session_id: str, role: str, content: str) -> MemoryEvent:
        return MemoryEvent(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )

# 3. REFACTOR: Improve code quality
class MemoryService:
    def __init__(self, repository: MemoryRepository, event_bus: EventBus):
        self._repository = repository
        self._event_bus = event_bus
    
    def create_event(self, session_id: str, role: str, content: str) -> MemoryEvent:
        event = MemoryEvent.create(session_id, role, content)
        self._repository.save(event)
        self._event_bus.publish(MemoryEventCreated(event))
        return event
```

### 6.3 テスト構成

```
tests/
├── unit/                               # Unit Tests
│   ├── domain/
│   │   ├── test_session.py
│   │   ├── test_memory_event.py
│   │   └── test_agent_response.py
│   ├── application/
│   │   ├── test_create_session_handler.py
│   │   ├── test_create_event_handler.py
│   │   └── test_invoke_agent_handler.py
│   └── infrastructure/
│       ├── test_memory_repository.py
│       └── test_vector_store.py
│
├── integration/                        # Integration Tests
│   ├── test_memory_service.py
│   ├── test_vector_search.py
│   ├── test_graph_queries.py
│   └── test_agent_invocation.py
│
├── e2e/                                # End-to-End Tests
│   ├── test_memory_flow.py
│   ├── test_multimodal_flow.py
│   └── test_voice_flow.py
│
└── fixtures/                           # Test Fixtures
    ├── sessions.py
    ├── events.py
    └── responses.py
```

---

## 7. ディレクトリ構造 (最終形)

```
rd-knowledge-sample/
├── app/                                # Frontend (Next.js + Amplify Gen2)
│   ├── amplify/                        # Amplify Backend Definition
│   │   ├── auth/
│   │   │   └── resource.ts
│   │   ├── data/
│   │   │   └── resource.ts             # GraphQL Schema (CQRS)
│   │   ├── functions/
│   │   │   ├── memory-resolver/        # Memory Service Lambda
│   │   │   ├── vector-resolver/        # Vector Service Lambda
│   │   │   ├── graph-resolver/         # Graph Service Lambda
│   │   │   └── agent-resolver/         # Agent Service Lambda
│   │   ├── storage/
│   │   │   └── resource.ts
│   │   └── backend.ts
│   │
│   ├── (features)/                     # FSD Feature Slices
│   │   ├── memory/
│   │   ├── multimodal/
│   │   └── voice/
│   │
│   ├── shared/                         # Shared Layer
│   │   ├── ui/                         # Atomic Design
│   │   │   ├── atoms/
│   │   │   ├── molecules/
│   │   │   ├── organisms/
│   │   │   └── templates/
│   │   ├── api/
│   │   └── lib/
│   │
│   ├── entities/                       # Domain Types
│   ├── widgets/                        # Composed Widgets
│   └── (routes)/                       # Next.js Routes
│
├── services/                           # Backend Microservices
│   ├── memory/                         # Memory Bounded Context
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   │   ├── session.py
│   │   │   │   └── memory_event.py
│   │   │   ├── events/
│   │   │   │   ├── session_started.py
│   │   │   │   └── memory_event_created.py
│   │   │   ├── value_objects/
│   │   │   │   └── session_id.py
│   │   │   └── repositories/
│   │   │       └── memory_repository.py
│   │   ├── application/
│   │   │   ├── commands/
│   │   │   │   ├── create_session.py
│   │   │   │   └── create_event.py
│   │   │   ├── queries/
│   │   │   │   ├── get_session.py
│   │   │   │   └── get_events.py
│   │   │   └── handlers/
│   │   │       ├── command_handlers.py
│   │   │       └── query_handlers.py
│   │   └── infrastructure/
│   │       ├── agentcore_memory_repository.py
│   │       └── event_store.py
│   │
│   ├── search/                         # Search Bounded Context
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   └── agent/                          # Agent Bounded Context
│       ├── domain/
│       ├── application/
│       └── infrastructure/
│
├── shared/                             # Shared Kernel
│   ├── domain/
│   │   ├── events/
│   │   │   └── domain_event.py
│   │   └── value_objects/
│   │       └── entity_id.py
│   ├── infrastructure/
│   │   ├── event_bus/
│   │   │   └── eventbridge_bus.py
│   │   └── observability/
│   │       └── xray_tracer.py
│   └── api/
│       └── graphql_types.py
│
├── tests/                              # TDD Tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── docs/                               # Documentation
│   ├── ARCHITECTURE_DESIGN.md          # This file
│   ├── RDRA_REQUIREMENTS.md
│   ├── EVENT_STORMING.md
│   └── API_REFERENCE.md
│
├── infra/                              # Legacy CDK (deprecated)
├── docker-compose.yml                  # Local Development
└── package.json
```

---

## 8. 実装ロードマップ

| Phase | 内容 | 期間 | 優先度 |
|-------|------|------|--------|
| Phase 1 | RDRA 要件分析完了 | 1日 | Critical |
| Phase 2 | DDD + Event Storming 完了 | 1日 | Critical |
| Phase 3 | Domain Layer 実装 (TDD) | 2日 | High |
| Phase 4 | Application Layer 実装 (CQRS) | 2日 | High |
| Phase 5 | Infrastructure Layer 実装 | 2日 | High |
| Phase 6 | Frontend FSD + Atomic 実装 | 3日 | High |
| Phase 7 | 統合テスト・E2E テスト | 2日 | Critical |
| Phase 8 | 本番デプロイ・検証 | 1日 | Critical |

---

## 付録: 技術スタック

| レイヤー | 技術 |
|---------|------|
| Frontend Framework | Next.js 14 (App Router) |
| Frontend Design | FSD + Atomic Design |
| State Management | Zustand / React Query |
| API Layer | Amplify Gen2 + AppSync (GraphQL) |
| Backend Pattern | Clean Architecture + CQRS + ES |
| Backend Runtime | AWS Lambda (TypeScript/Python) |
| Domain Events | AgentCore Memory / EventBridge |
| Vector Store | S3 Vectors / Bedrock KB |
| Graph Store | Neo4j AuraDB |
| AI/ML | Bedrock (Nova), StrandsAgents |
| Auth | Cognito (Amplify Auth) |
| CI/CD | Amplify Hosting |
| Testing | Vitest, Pytest, Playwright |
| Observability | X-Ray, CloudWatch, CloudTrail |
