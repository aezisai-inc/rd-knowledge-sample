# クリーンアーキテクチャ設計

## 1. アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                           Presentation Layer                                 │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │  AppSync GraphQL  │  Lambda Resolvers  │  Next.js Frontend         │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │                       Application Layer                             │  │
│    │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │  │
│    │  │ Command Handler│  │ Query Handler  │  │ Event Handler  │        │  │
│    │  └────────────────┘  └────────────────┘  └────────────────┘        │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │                         Domain Layer                                │  │
│    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│    │  │  Aggregates  │  │  Entities    │  │ Value Objects│              │  │
│    │  └──────────────┘  └──────────────┘  └──────────────┘              │  │
│    │  ┌──────────────┐  ┌──────────────┐                                │  │
│    │  │Domain Events │  │Domain Service│                                │  │
│    │  └──────────────┘  └──────────────┘                                │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │                       Infrastructure Layer                          │  │
│    │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │  │
│    │  │ Repository Impl│  │ External APIs  │  │ Event Bus      │        │  │
│    │  └────────────────┘  └────────────────┘  └────────────────┘        │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. 依存性の方向

```
                    依存の方向
                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  Presentation  →  Application  →  Domain  ←  Infrastructure                 │
└─────────────────────────────────────────────────────────────────────────────┘

Domain Layer は他のどのレイヤーにも依存しない（最内層）
Infrastructure は Domain のインターフェースを実装（依存性逆転）
```

## 3. レイヤー詳細

### 3.1 Domain Layer（最内層）

**責務**: ビジネスロジック、ビジネスルールの表現

```python
# entities/session.py
@dataclass
class Session:
    """Session 集約ルート - ビジネスルールを内包"""
    
    def add_event(self, role: Role, content: Content) -> MemoryEvent:
        """ビジネスルール: 終了済みセッションへの追加禁止"""
        if self.is_ended:
            raise ValueError("Cannot add events to an ended session")
        # ...
```

**構成要素**:
- エンティティ（Entity）
- 値オブジェクト（Value Object）
- 集約（Aggregate）
- ドメインサービス（Domain Service）
- ドメインイベント（Domain Event）
- リポジトリインターフェース（Repository Interface）

### 3.2 Application Layer

**責務**: ユースケースの調整、トランザクション境界

```python
# handlers/command_handlers.py
class CreateSessionHandler:
    """ユースケース: セッション作成"""
    
    def __init__(self, repository: SessionRepository):
        self._repository = repository  # 依存性注入
    
    async def handle(self, command: CreateSessionCommand) -> CreateSessionResult:
        # 1. ドメインオブジェクト作成
        session = Session.create(...)
        
        # 2. 永続化
        await self._repository.save(session)
        
        # 3. 結果返却
        return CreateSessionResult(...)
```

**構成要素**:
- コマンド（Command）
- クエリ（Query）
- コマンドハンドラ（Command Handler）
- クエリハンドラ（Query Handler）
- DTO（Data Transfer Object）

### 3.3 Infrastructure Layer

**責務**: 技術的関心事、外部サービス連携

```python
# repositories/in_memory_session_repository.py
class InMemorySessionRepository:
    """SessionRepository の実装"""
    
    async def save(self, session: Session) -> None:
        self._sessions[str(session.id)] = session
    
    async def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        return self._sessions.get(str(session_id))
```

**構成要素**:
- リポジトリ実装
- 外部 API クライアント
- イベントバス実装
- ロギング、トレーシング

### 3.4 Presentation Layer

**責務**: 外部インターフェース、入出力変換

```typescript
// GraphQL Resolver
export const handler = async (event: AppSyncResolverEvent<any>) => {
  const { fieldName } = event.info;
  
  switch (fieldName) {
    case 'createMemorySession':
      return await createSessionHandler.handle(event.arguments);
    // ...
  }
};
```

## 4. CQRS パターン

### Command（書き込み）側

```
Command → Command Handler → Domain → Repository → Event Store
```

```python
# コマンド定義
@dataclass(frozen=True)
class CreateSessionCommand:
    actor_id: str
    session_type: str
    title: Optional[str] = None

# ハンドラ
class CreateSessionHandler:
    async def handle(self, command: CreateSessionCommand) -> CreateSessionResult:
        session = Session.create(...)  # ドメインロジック
        await self._repository.save(session)  # 永続化
        return CreateSessionResult(session_id=str(session.id))
```

### Query（読み取り）側

```
Query → Query Handler → Read Model → DTO
```

```python
# クエリ定義
@dataclass(frozen=True)
class GetSessionQuery:
    session_id: str

# ハンドラ
class GetSessionHandler:
    async def handle(self, query: GetSessionQuery) -> SessionDto:
        session = await self._repository.find_by_id(...)
        return SessionDto(...)  # 読み取り最適化された DTO
```

## 5. イベントソーシング

### イベントストア

```python
# ドメインイベントの永続化
class EventStore:
    async def append(self, aggregate_id: str, events: List[DomainEvent]) -> None:
        """イベントを追記"""
        for event in events:
            await self._store.put_item(
                PK=f"AGGREGATE#{aggregate_id}",
                SK=f"EVENT#{event.version}",
                event_data=event.to_dict(),
            )
    
    async def get_events(self, aggregate_id: str) -> List[DomainEvent]:
        """集約のイベント履歴を取得"""
        # イベントから集約を再構築可能
        pass
```

### 集約の再構築

```python
class Session:
    @classmethod
    def from_events(cls, events: List[DomainEvent]) -> Session:
        """イベント履歴から集約を再構築"""
        session = cls.__new__(cls)
        for event in events:
            session.apply(event)
        return session
    
    def apply(self, event: DomainEvent) -> None:
        """イベントを適用"""
        if isinstance(event, SessionStarted):
            self._apply_session_started(event)
        elif isinstance(event, MemoryEventCreated):
            self._apply_memory_event_created(event)
        # ...
```

## 6. 依存性逆転の原則（DIP）

### Protocol による抽象化

```python
# domain/repositories/session_repository.py (Domain Layer)
class SessionRepository(Protocol):
    """リポジトリインターフェース（Domain 層で定義）"""
    
    async def save(self, session: Session) -> None: ...
    async def find_by_id(self, session_id: SessionId) -> Optional[Session]: ...

# infrastructure/repositories/in_memory_session_repository.py
class InMemorySessionRepository:
    """実装（Infrastructure 層）"""
    
    async def save(self, session: Session) -> None:
        # 実際の永続化ロジック
        pass
```

### 依存性注入

```python
# アプリケーション起動時
repository = InMemorySessionRepository()  # 実装を選択
handler = CreateSessionHandler(repository)  # 依存性注入

# テスト時
mock_repository = MockSessionRepository()  # テスト用実装
handler = CreateSessionHandler(mock_repository)
```

## 7. ディレクトリ構造

```
services/memory/
├── domain/                     # Domain Layer
│   ├── entities/
│   │   └── session.py         # Session 集約
│   ├── value_objects/
│   │   └── session_id.py      # 値オブジェクト
│   ├── events/
│   │   └── session_events.py  # ドメインイベント
│   └── repositories/
│       └── session_repository.py  # インターフェース
│
├── application/                # Application Layer
│   ├── commands/
│   │   └── session_commands.py
│   ├── queries/
│   │   └── session_queries.py
│   └── handlers/
│       ├── command_handlers.py
│       └── query_handlers.py
│
└── infrastructure/             # Infrastructure Layer
    ├── repositories/
    │   ├── in_memory_session_repository.py
    │   └── agentcore_session_repository.py
    └── external/
        └── bedrock_client.py
```

---

**作成日**: 2026-01-03
**更新日**: 2026-01-03
