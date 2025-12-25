# 🧠 Graphiti × A2A Standard 統合設計書

> **Agent 間関係グラフ専用ナレッジグラフシステム**

## 📖 概要

### Graphiti の役割

**⚠️ 重要: Graphiti は Agent 間の関係グラフ専用**

| 記憶タイプ | 担当システム | Graphiti での使用 |
|-----------|-------------|------------------|
| 短期記憶 | AgentCore Memory | ❌ 使用しない |
| エピソード記憶 | AgentCore Memory | ❌ 使用しない |
| セマンティック記憶 | AgentCore Memory | ❌ 使用しない |
| **関係グラフ** | **Graphiti** | ✅ 専用 |

### Graphiti が解決する課題

1. **Agent 間依存関係の可視化**
   - どの Agent がどの Agent に依存しているか
   - 障害時の影響範囲分析

2. **ルーティング最適化**
   - 過去の成功ルートの追跡
   - 動的なルーティング決定

3. **時系列での関係変化追跡**
   - 双時間モデルによる履歴管理
   - 「1ヶ月前の構成」の再現

---

## 🎯 データモデル設計

### EntityNode (Agent エンティティ)

**用途**: Agent の静的情報を表現（記憶ではなくカタログ情報）

```python
class AgentNode:
    """Agent を表す EntityNode（カタログ情報）"""
    id: str                    # Agent ID
    name: str                  # 表示名
    agent_type: str            # タイプ (registry, gateway, orchestration, etc.)
    capabilities: list[str]    # 能力リスト
    endpoint: str              # エンドポイント URL
    status: str                # 状態 (active/inactive/deprecated)
    # ※ 個別 Agent の記憶は AgentCore Memory で管理
```

### EntityEdge (Agent 間関係) ← **主要用途**

**用途**: Agent 間の動的関係を表現

```python
class AgentRelation:
    """Agent 間の関係を表す EntityEdge"""
    source_agent_id: str       # 起点 Agent
    target_agent_id: str       # 終点 Agent
    relation_type: str         # 関係タイプ
    # 関係タイプ:
    # - DELEGATES_TO: タスク委譲
    # - DEPENDS_ON: 機能依存
    # - ROUTES_TO: ルーティング
    # - COLLABORATES_WITH: 協調
    # - REPLACES: 代替関係
    fact: str                  # 関係の自然言語記述
    weight: float              # 関係の強度 (0.0-1.0)
    context: dict              # 追加コンテキスト
    valid_from: datetime       # 有効開始日時
    valid_to: datetime         # 有効終了日時 (null = 現在有効)
```

### EpisodicNode (関係イベント) ← **関係変化の記録用**

**用途**: Agent 間関係の変化イベントを記録（個別 Agent の記憶ではない）

```python
class RelationEvent:
    """関係変化イベント（システムレベル）"""
    event_type: str            # created, updated, removed
    source_agent_id: str
    target_agent_id: str
    relation_type: str
    reason: str                # 変化理由
    triggered_by: str          # トリガー (orchestration, admin, auto)
    event_time: datetime       # イベント発生時刻
    ingestion_time: datetime   # データ取り込み時刻
```

---

## 🏗️ アーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    A2A Standard Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AgentCore Memory (個別 Agent 記憶)           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │  │
│  │  │Short-term│ │Episodic  │ │Semantic  │ │Reflections│   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │  │
│  │                                                          │  │
│  │  Registry Agent | Gateway Agent | Orchestration Agent    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              │ 関係情報のみ                     │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Graphiti (Agent 間関係グラフ)                │  │
│  │                                                          │  │
│  │    [Registry] ──ROUTES_TO──▶ [Gateway]                   │  │
│  │        │                         │                       │  │
│  │        │                         │                       │  │
│  │   DEPENDS_ON               DELEGATES_TO                  │  │
│  │        │                         │                       │  │
│  │        ▼                         ▼                       │  │
│  │    [Identity] ◀──COLLABORATES──▶ [Orchestration]        │  │
│  │                                                          │  │
│  │    ※ 個別 Agent の記憶はここには保存しない               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 連携フロー

```
1. Agent 登録時
   └─▶ Graphiti: Agent ノード作成（カタログ情報のみ）

2. Agent 間通信発生時
   └─▶ Graphiti: 関係エッジ作成/更新

3. タスク実行時 (個別 Agent 内)
   └─▶ AgentCore Memory: エピソード記憶保存
   └─▶ Graphiti: Agent 間呼び出し関係のみ記録

4. ルーティング決定時
   └─▶ Graphiti: 過去の成功ルートを検索
   └─▶ AgentCore Memory: 過去のタスク結果を参照

5. 障害分析時
   └─▶ Graphiti: 影響範囲をグラフトラバーサルで特定
```

---

## 🔧 実装設計

### Graphiti Adapter (修正版)

```python
class GraphitiRelationAdapter:
    """
    Agent 間関係グラフ専用アダプター
    
    ⚠️ 個別 Agent のエピソード/セマンティック記憶は
       AgentCore Memory を使用すること
    """
    
    async def register_agent_node(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: list[str],
    ) -> None:
        """Agent をノードとして登録（カタログ情報のみ）"""
        pass
    
    async def record_agent_relation(
        self,
        source_agent_id: str,
        target_agent_id: str,
        relation_type: str,  # DELEGATES_TO, DEPENDS_ON, ROUTES_TO, etc.
        fact: str,
        context: dict = None,
    ) -> None:
        """Agent 間関係を記録"""
        pass
    
    async def update_relation(
        self,
        source_agent_id: str,
        target_agent_id: str,
        relation_type: str,
        updates: dict,
    ) -> None:
        """関係を更新"""
        pass
    
    async def remove_relation(
        self,
        source_agent_id: str,
        target_agent_id: str,
        relation_type: str,
        reason: str,
    ) -> None:
        """関係を無効化（履歴は保持）"""
        pass
    
    async def find_related_agents(
        self,
        agent_id: str,
        relation_type: str = None,
        direction: str = "outgoing",  # outgoing, incoming, both
    ) -> list[dict]:
        """関連 Agent を検索"""
        pass
    
    async def find_impact_scope(
        self,
        agent_id: str,
        max_depth: int = 3,
    ) -> list[dict]:
        """障害影響範囲を分析"""
        pass
    
    async def get_routing_history(
        self,
        source_agent_id: str,
        target_capability: str,
    ) -> list[dict]:
        """過去のルーティング履歴を取得"""
        pass
```

### 使用例

```python
# ✅ 正しい使用: Agent 間関係の記録
await graphiti.record_agent_relation(
    source_agent_id="gateway-agent",
    target_agent_id="registry-agent",
    relation_type="DELEGATES_TO",
    fact="Gateway Agent が Agent 検索を Registry Agent に委譲",
    context={"task_type": "search_agents"}
)

# ✅ 正しい使用: 影響分析
impact = await graphiti.find_impact_scope(
    agent_id="registry-agent",
    max_depth=2
)
# → ["gateway-agent", "orchestration-agent", ...]

# ❌ 誤った使用: タスク結果の記憶 → AgentCore Memory を使う
# await graphiti.record_task_execution(...)  # NG!

# ✅ 代わりに AgentCore Memory を使用
await agentcore_memory.save_episodic(
    session_id=session_id,
    event={
        "type": "task_completed",
        "task_id": task_id,
        "result": result,
        "learnings": ["..."]
    }
)
```

---

## 🚀 AWS デプロイ構成

### 構成 (関係グラフ専用に最適化)

```yaml
resources:
  neo4j:
    type: EC2 t3.small  # 関係グラフのみなので小さめ
    storage: EBS 20GB
    cost: ~$20/月
    
  graphiti_service:
    type: Fargate 0.25vCPU/0.5GB
    cost: ~$15/月
    
  load_balancer:
    type: ALB (internal)
    cost: ~$20/月
    
  total_cost: ~$55-70/月  # 記憶を含めないため削減
```

### 代替: Neptune (AWS ネイティブ)

関係グラフのみであれば、Amazon Neptune も選択肢：

```yaml
neptune:
  type: db.t3.medium
  cost: ~$50/月
  pros:
    - AWS マネージド
    - Gremlin/openCypher 対応
    - IAM 統合
  cons:
    - Graphiti の双時間モデルは手動実装
    - ハイブリッド検索は別途実装
```

---

## 📋 チェックリスト

### 設計時の確認

- [ ] この情報は「Agent 間の関係」か？ → Graphiti
- [ ] この情報は「個別 Agent の経験・知識」か？ → AgentCore Memory
- [ ] 時系列での関係変化を追跡する必要があるか？ → Graphiti
- [ ] グラフトラバーサル（影響分析等）が必要か？ → Graphiti

### 実装時の確認

- [ ] `record_task_execution` を Graphiti に呼んでいないか
- [ ] `save_episodic` / `save_semantic` は AgentCore Memory を使用しているか
- [ ] Agent 間関係のみ Graphiti に記録しているか

---

## 🔗 関連ドキュメント

- [RESEARCH_AGENT_MEMORY_SYSTEMS.md](./RESEARCH_AGENT_MEMORY_SYSTEMS.md) - 調査報告
- [MEMORY_ARCHITECTURE_DESIGN.md](./MEMORY_ARCHITECTURE_DESIGN.md) - AgentCore メモリ設計

---

## 📅 更新履歴

| 日付 | 内容 |
|------|------|
| 2025-12-25 | 初版作成 |
| 2025-12-25 | **修正**: Agent 間関係グラフ専用に役割限定。エピソード/セマンティック記憶は AgentCore Memory へ移行 |
