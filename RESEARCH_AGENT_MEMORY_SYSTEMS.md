# 🔬 AI Agent メモリシステム調査報告

> **調査日**: 2025-12-25  
> **調査目的**: AgentCore Memory と Graphiti の役割分担明確化

---

## 📋 調査背景

A2A Standard Platform の設計において、以下の2つのメモリシステムの統合を検討した：

1. **AWS Bedrock AgentCore Memory** - AWS が提供するマネージド Agent メモリ
2. **Graphiti** - 時間認識型ナレッジグラフフレームワーク

初期設計では Graphiti の EpisodicNode/EntityNode を Agent のエピソード記憶・セマンティック記憶として使用する案があったが、これは AgentCore Memory の役割と重複するため、適切な役割分担が必要。

---

## 📊 各システムの特徴比較

### 1. AWS Bedrock AgentCore Memory

| 特徴 | 詳細 |
|------|------|
| **提供形態** | AWS マネージドサービス |
| **記憶タイプ** | Short-term, Episodic, Semantic, Reflections |
| **ストレージ** | AWS 内部 (DynamoDB/S3ベース推定) |
| **API** | Bedrock Agent Runtime API |
| **課金** | 使用量ベース |

**記憶タイプ詳細:**

```python
# Short-term Memory (短期記憶)
# - セッション中の会話コンテキスト
# - 最近のやり取り
short_term = {
    "session_id": "sess-123",
    "messages": [...],
    "context": {...}
}

# Episodic Memory (エピソード記憶)
# - 過去のタスク実行経験
# - 成功/失敗パターン
episodic = {
    "event_type": "task_completed",
    "task_id": "task-456",
    "outcome": "success",
    "learnings": ["パターンA は効果的", "パターンB は避けるべき"],
    "timestamp": "2025-12-25T10:00:00Z"
}

# Semantic Memory (セマンティック記憶)
# - 学習した知識・事実
# - ドメイン固有の情報
semantic = {
    "fact_type": "domain_knowledge",
    "content": "ユーザーXは日本語を好む",
    "confidence": 0.95,
    "source": "interaction_analysis"
}

# Reflections (リフレクション)
# - 自己分析・改善点
# - メタ認知情報
reflection = {
    "analysis_type": "performance_review",
    "insight": "複雑なクエリには段階的アプローチが有効",
    "action_item": "長いタスクは分割して処理する"
}
```

### 2. Graphiti

| 特徴 | 詳細 |
|------|------|
| **提供形態** | OSS (Python) + Neo4j |
| **データモデル** | EntityNode, EpisodicNode, EntityEdge |
| **ストレージ** | Neo4j (Graph Database) |
| **検索** | ハイブリッド (Semantic + Keyword + Graph) |
| **特徴** | 双時間モデル、リアルタイム増分更新 |

**データモデル詳細:**

```python
# EntityNode - エンティティ（人、場所、概念など）
entity_node = {
    "uuid": "ent-001",
    "name": "Registry Agent",
    "entity_type": "AGENT",
    "properties": {...},
    "embedding": [0.1, 0.2, ...],  # 検索用ベクトル
    "created_at": "2025-12-25T10:00:00Z",
    "valid_at": "2025-12-25T10:00:00Z"  # 双時間モデル
}

# EpisodicNode - イベント・エピソード
episodic_node = {
    "uuid": "ep-001",
    "name": "agent_interaction",
    "content": "Agent A が Agent B にタスクを委譲",
    "source": "orchestration_log",
    "embedding": [0.3, 0.4, ...],
    "event_time": "2025-12-25T10:00:00Z",    # イベント発生時刻
    "ingestion_time": "2025-12-25T10:01:00Z" # データ取り込み時刻
}

# EntityEdge - 関係
entity_edge = {
    "uuid": "edge-001",
    "source_node": "ent-001",
    "target_node": "ent-002",
    "relation_type": "DELEGATES_TO",
    "fact": "Registry Agent は Gateway Agent にルーティングを委譲する",
    "weight": 0.9,
    "valid_from": "2025-12-25T10:00:00Z",
    "valid_to": null  # 現在有効
}
```

---

## 🎯 調査結論: 役割分担

### ❌ 誤った設計 (初期案)

```
Graphiti
├── EntityNode → Agent のセマンティック記憶 (重複!)
├── EpisodicNode → Agent のエピソード記憶 (重複!)
└── EntityEdge → Agent 間関係
```

**問題点:**
1. AgentCore Memory と機能重複
2. 2つのシステムに記憶が分散し管理困難
3. AgentCore の最適化された記憶検索を活用できない

### ✅ 正しい設計

```
┌─────────────────────────────────────────────────────────────┐
│                    記憶システム役割分担                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【個別Agent の記憶】                                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           AgentCore Memory (Bedrock)                  │ │
│  │                                                       │ │
│  │  • Short-term: セッションコンテキスト                 │ │
│  │  • Episodic: タスク実行経験・学習                     │ │
│  │  • Semantic: ドメイン知識・ユーザー情報               │ │
│  │  • Reflections: 自己分析・改善                        │ │
│  │                                                       │ │
│  │  → Agent 個別の「脳」として機能                       │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  【システム全体の関係グラフ】                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Graphiti (Neo4j)                         │ │
│  │                                                       │ │
│  │  • Agent 間の依存関係                                 │ │
│  │  • Agent 間の委譲・ルーティング関係                   │ │
│  │  • 時系列での関係変化追跡                             │ │
│  │  • システム全体のトポロジー                           │ │
│  │                                                       │ │
│  │  → システムの「神経網」として機能                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 具体的な使い分けガイドライン

### AgentCore Memory を使うケース

| ユースケース | 記憶タイプ | 例 |
|-------------|-----------|-----|
| 会話コンテキスト維持 | Short-term | 現在のセッションでのやり取り |
| 過去のタスク結果参照 | Episodic | 「前回同じクエリでは X が効果的だった」 |
| ユーザー嗜好学習 | Semantic | 「このユーザーは日本語を好む」 |
| 自己改善 | Reflections | 「複雑なタスクは分割すると効率的」 |
| パーソナライゼーション | Semantic | 「ユーザーAの業務ドメインは金融」 |

### Graphiti を使うケース

| ユースケース | データタイプ | 例 |
|-------------|------------|-----|
| Agent 依存関係管理 | EntityEdge | Registry → Gateway 依存 |
| ルーティング最適化 | EntityEdge | 過去の成功ルート |
| Agent 発見 | EntityNode | 能力ベースの Agent 検索 |
| 影響分析 | Graph Traversal | 「Agent X 停止時の影響範囲」 |
| 時系列関係追跡 | Bi-temporal | 「1ヶ月前の Agent 構成」 |

---

## 🔧 実装への反映

### 修正が必要なファイル

1. **GRAPHITI_INTEGRATION_DESIGN.md**
   - EpisodicNode/EntityNode を個別 Agent 記憶から削除
   - 関係グラフ（EntityEdge）に特化

2. **graphiti_adapter.py**
   - `record_agent_registered` → Agent 間関係記録に変更
   - `record_task_execution` → 削除 (AgentCore Memory へ移行)
   - `record_agent_interaction` → 維持 (Agent 間関係)

3. **新規: agentcore_memory_adapter.py**
   - AgentCore Memory との連携実装
   - エピソード記憶、セマンティック記憶の保存・検索

---

## 📚 参考資料

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Graphiti GitHub](https://github.com/getzep/graphiti)
- [Graphiti 技術調査 (Zenn)](https://zenn.dev/suwash/articles/graphithi_20250605)
- [MEMORY_ARCHITECTURE_DESIGN.md](./MEMORY_ARCHITECTURE_DESIGN.md)

---

## 📅 更新履歴

| 日付 | 内容 |
|------|------|
| 2025-12-25 | 初版作成: AgentCore Memory vs Graphiti 役割分担調査 |




