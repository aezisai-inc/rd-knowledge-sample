# DDD ドメインモデル設計

## 1. 戦略的設計

### 1.1 ドメインビジョン

> AI エージェントの記憶・検索・対話を統合した
> 知識管理システムを実現する

### 1.2 境界付けられたコンテキスト

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Knowledge Sample                                  │
├────────────────────┬────────────────────┬──────────────────────────────┤
│   Memory Context   │   Search Context   │      Agent Context           │
│                    │                    │                              │
│   会話履歴の管理   │   情報の検索       │   AI エージェント対話        │
│   セッション永続化 │   ベクトル検索     │   マルチモーダル処理         │
│                    │                    │                              │
│   [Core Domain]    │   [Supporting]     │   [Core Domain]              │
└────────────────────┴────────────────────┴──────────────────────────────┘
```

### 1.3 コンテキストマップ

```
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│   Memory    │◀──────▶│   Search    │◀──────▶│   Agent     │
│   Context   │  OHS   │   Context   │  OHS   │   Context   │
└─────────────┘        └─────────────┘        └─────────────┘
       │                      │                      │
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐        ┌─────────────┐        ┌─────────────┐
│  AgentCore  │        │  S3 Vector  │        │  Bedrock    │
│  Memory     │        │  Store      │        │  Nova       │
└─────────────┘        └─────────────┘        └─────────────┘

OHS = Open Host Service (公開ホストサービス)
```

## 2. 戦術的設計

### 2.1 Memory Context

#### 集約: Session

```python
# Session 集約ルート
class Session:
    """
    会話セッション集約
    
    不変条件:
    - session_id はシステム全体で一意
    - ended_at が設定された後は events 追加不可
    - event_count は events の実際の数と一致
    """
    id: SessionId
    actor_id: ActorId
    session_type: SessionType
    started_at: datetime
    ended_at: Optional[datetime]
    events: List[MemoryEvent]  # 子エンティティ
```

#### エンティティ: MemoryEvent

```python
class MemoryEvent:
    """
    セッション内のイベント
    
    不変条件:
    - event_id は session 内で一意
    - timestamp は作成時に自動設定
    """
    id: EventId
    session_id: SessionId
    role: Role
    content: Content
    timestamp: datetime
```

#### 値オブジェクト

```python
@dataclass(frozen=True)
class SessionId(EntityId):
    """セッション識別子"""
    pass

@dataclass(frozen=True)
class Role:
    """発話者ロール"""
    value: str  # USER | ASSISTANT | SYSTEM | TOOL
    
@dataclass(frozen=True)
class Content:
    """メッセージ内容"""
    value: str
```

### 2.2 Search Context

#### 集約: VectorIndex

```python
class VectorIndex:
    """ベクトルインデックス集約"""
    id: IndexId
    name: str
    dimensions: int
    documents: List[Document]
```

#### エンティティ: Document

```python
class Document:
    """検索対象ドキュメント"""
    id: DocumentId
    content: str
    embedding: VectorEmbedding
    metadata: dict
```

### 2.3 Agent Context

#### 集約: AgentSession

```python
class AgentSession:
    """エージェント対話セッション"""
    id: AgentSessionId
    agent_type: AgentType  # multimodal | voice
    memory_session_id: SessionId
    tools: List[Tool]
```

## 3. ドメインサービス

### 3.1 Memory Domain Service

```python
class MemoryService:
    """Memory コンテキストのドメインサービス"""
    
    async def start_session(
        self, actor_id: ActorId, session_type: SessionType
    ) -> Session:
        """新規セッションを開始"""
        pass
    
    async def add_event(
        self, session_id: SessionId, role: Role, content: Content
    ) -> MemoryEvent:
        """セッションにイベントを追加"""
        pass
```

### 3.2 Search Domain Service

```python
class SearchService:
    """Search コンテキストのドメインサービス"""
    
    async def search(
        self, query: str, k: int = 10
    ) -> List[SearchResult]:
        """セマンティック検索"""
        pass
```

### 3.3 Agent Domain Service

```python
class AgentService:
    """Agent コンテキストのドメインサービス"""
    
    async def invoke(
        self, session_id: SessionId, prompt: str, image: Optional[bytes] = None
    ) -> AgentResponse:
        """エージェントを呼び出し"""
        pass
```

## 4. リポジトリ

### 4.1 Session Repository

```python
class SessionRepository(Protocol):
    """Session 集約のリポジトリインターフェース"""
    
    async def save(self, session: Session) -> None:
        """セッションを保存"""
        ...
    
    async def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        """ID でセッションを取得"""
        ...
    
    async def find_by_actor_id(self, actor_id: ActorId) -> List[Session]:
        """Actor のセッションを取得"""
        ...
```

## 5. ドメインイベント

### 5.1 Memory Context Events

```python
@dataclass(frozen=True)
class SessionStarted(DomainEvent):
    """セッション開始イベント"""
    session_id: str
    actor_id: str
    session_type: str

@dataclass(frozen=True)
class MemoryEventCreated(DomainEvent):
    """メモリイベント作成イベント"""
    session_id: str
    event_id: str
    role: str
    content: str

@dataclass(frozen=True)
class SessionEnded(DomainEvent):
    """セッション終了イベント"""
    session_id: str
    event_count: int
    duration_seconds: float
```

## 6. ユビキタス言語

| 用語（英語） | 用語（日本語） | 定義 |
|-------------|---------------|------|
| Session | セッション | 一連の会話やり取りの単位 |
| MemoryEvent | メモリイベント | セッション内の個々の発話・行動 |
| Actor | アクター | ユーザーまたは AI エージェント |
| Role | ロール | 発話者の種類（USER/ASSISTANT/SYSTEM/TOOL） |
| Content | コンテンツ | メッセージの本文 |
| VectorEmbedding | ベクトル埋め込み | テキストの数値表現 |
| AgentSession | エージェントセッション | AI エージェントとの対話セッション |

---

**作成日**: 2026-01-03
**更新日**: 2026-01-03
