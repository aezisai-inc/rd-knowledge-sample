# TDD テスト戦略ドキュメント

## 概要

rd-knowledge-sample プロジェクトのテスト駆動開発（TDD）戦略。
Red-Green-Refactor サイクルに基づき、ドメインモデルから実装を駆動。

## テストピラミッド

```
                    ╭─────────────╮
                   │    E2E      │  ← UI 統合テスト
                  ╱│   Tests    │╲    (少数・重要フロー)
                 ╱ ╰─────────────╯ ╲
                ╱                   ╲
               ╭───────────────────────╮
              │   Integration Tests    │  ← CQRS ハンドラ統合
             ╱│                       │╲    (中程度)
            ╱ ╰───────────────────────╯ ╲
           ╱                             ╲
          ╭───────────────────────────────────╮
         │         Unit Tests                  │  ← ドメインモデル
         │                                     │    (大量・高速)
         ╰───────────────────────────────────╯
```

## テストカテゴリ

### 1. Unit Tests（ドメイン層）

**場所**: `tests/unit/domain/`

**対象**:
- 値オブジェクト（EntityId, Role, Content 等）
- エンティティ（Session, MemoryEvent）
- ドメインイベント（SessionStarted, MemoryEventCreated）
- 集約ルート（Session Aggregate）

**特徴**:
- 外部依存なし（Pure Domain）
- ミリ秒で実行
- ビジネスルールの検証

```python
# テスト例: Session 集約
def test_add_event_to_ended_session_should_raise_error():
    """終了済みセッションへのイベント追加はエラー"""
    session = Session.create(ActorId.generate(), SessionType.memory())
    session.end()
    
    with pytest.raises(ValueError, match="Cannot add events"):
        session.add_event(Role.user(), Content("Hello"))
```

### 2. Integration Tests（アプリケーション層）

**場所**: `tests/integration/`

**対象**:
- Command Handlers（Write 側）
- Query Handlers（Read 側）
- Repository 実装

**特徴**:
- インメモリリポジトリ使用
- CQRS パターンの検証
- 非同期処理のテスト

```python
# テスト例: 完全なワークフロー
@pytest.mark.asyncio
async def test_complete_session_workflow(handlers):
    # 1. セッション作成
    create_result = await handlers.create.handle(
        CreateSessionCommand(actor_id=str(ActorId.generate()), session_type="voice")
    )
    
    # 2. イベント追加
    await handlers.add_event.handle(
        AddEventCommand(session_id=create_result.session_id, role="USER", content="Hello")
    )
    
    # 3. セッション終了
    await handlers.end.handle(EndSessionCommand(session_id=create_result.session_id))
```

### 3. E2E Tests（プレゼンテーション層）

**場所**: `tests/e2e/`

**対象**:
- GraphQL API エンドポイント
- フロントエンド統合
- 実際の AWS サービス（オプション）

**特徴**:
- 実際の API 呼び出し
- ブラウザ自動化（Playwright）
- 本番に近い環境

```python
# テスト例: GraphQL E2E
@pytest.mark.e2e
async def test_create_session_via_graphql(client):
    mutation = '''
    mutation CreateSession($input: CreateSessionInput!) {
        createSession(input: $input) {
            sessionId
            startedAt
        }
    }
    '''
    result = await client.execute(mutation, {"input": {"sessionType": "memory"}})
    assert result["createSession"]["sessionId"] is not None
```

## TDD サイクル

### Red-Green-Refactor

```
┌─────────────┐
│   RED       │  1. 失敗するテストを書く
│  (Failing)  │     - ビジネス要件をテストで表現
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   GREEN     │  2. 最小限のコードで通す
│  (Passing)  │     - テストを通すだけの実装
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  REFACTOR   │  3. リファクタリング
│  (Clean)    │     - 重複除去、設計改善
└──────┬──────┘
       │
       └──────── 次のテストへ ────────▶
```

### 実装順序

1. **値オブジェクト** → 最も依存が少ない
2. **エンティティ** → 値オブジェクトを使用
3. **集約ルート** → エンティティを含む
4. **リポジトリ** → 集約の永続化
5. **ハンドラ** → ユースケース実装
6. **API** → 外部インターフェース

## テスト設計原則

### FIRST 原則

| 原則 | 説明 |
|------|------|
| **F**ast | 高速に実行（Unit: <10ms, Integration: <100ms） |
| **I**ndependent | 他テストに依存しない |
| **R**epeatable | 何度実行しても同じ結果 |
| **S**elf-validating | 自動で成功/失敗を判定 |
| **T**imely | 実装前にテストを書く |

### Given-When-Then（AAA）

```python
def test_example():
    # Given (Arrange): 前提条件
    session = Session.create(ActorId.generate(), SessionType.memory())
    
    # When (Act): テスト対象の実行
    event = session.add_event(Role.user(), Content("Hello"))
    
    # Then (Assert): 結果の検証
    assert session.event_count == 1
    assert event.role.is_user()
```

## テストカバレッジ目標

| レイヤー | カバレッジ目標 | 現状 |
|----------|---------------|------|
| Domain | 95%+ | 98% |
| Application | 90%+ | 95% |
| Infrastructure | 80%+ | - |
| Presentation | 70%+ | - |

## テスト実行コマンド

```bash
# 全テスト実行
pytest

# ユニットテストのみ
pytest tests/unit/ -v

# 統合テストのみ
pytest tests/integration/ -v

# E2E テストのみ
pytest tests/e2e/ -v -m e2e

# カバレッジ付き
pytest --cov=services --cov=shared --cov-report=html

# 並列実行
pytest -n auto

# 特定テスト
pytest tests/unit/domain/test_session.py::TestSession -v
```

## Mock / Stub 戦略

### 使用基準

| 状況 | 戦略 |
|------|------|
| ドメイン層 | モック不使用（Pure） |
| アプリケーション層 | インメモリリポジトリ |
| インフラ層 | ローカルスタック / Moto |
| 外部 API | VCR / Mock Server |

### AgentCore Memory テスト

```python
# インメモリ実装でテスト
class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions = {}
    
    async def save(self, session): ...
    async def find_by_id(self, id): ...

# 本番では AgentCore Memory に差し替え
# class AgentCoreSessionRepository(SessionRepository): ...
```

## CI/CD 統合

```yaml
# GitHub Actions
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Run Unit Tests
      run: pytest tests/unit/ -v --cov
    
    - name: Run Integration Tests
      run: pytest tests/integration/ -v
    
    - name: Run E2E Tests (on main only)
      if: github.ref == 'refs/heads/main'
      run: pytest tests/e2e/ -v -m e2e
```

## テストデータ管理

### Fixtures

```python
@pytest.fixture
def actor_id():
    """テスト用 ActorId"""
    return ActorId.generate()

@pytest.fixture
def sample_session(actor_id):
    """サンプルセッション"""
    session = Session.create(actor_id, SessionType.memory(), title="Test")
    session.add_event(Role.user(), Content("Hello"))
    session.add_event(Role.assistant(), Content("Hi!"))
    return session
```

### Factory パターン

```python
class SessionFactory:
    @staticmethod
    def create_with_events(event_count: int = 0) -> Session:
        session = Session.create(ActorId.generate(), SessionType.memory())
        for i in range(event_count):
            role = Role.user() if i % 2 == 0 else Role.assistant()
            session.add_event(role, Content(f"Message {i}"))
        return session
```

## 現在のテスト状況

### 実装済み

- ✅ Unit Tests: 27 件パス
- ✅ Integration Tests: 7 件パス
- ⏳ E2E Tests: 未実装

### 次のステップ

1. E2E テストの実装（GraphQL API）
2. フロントエンドコンポーネントテスト
3. Bedrock API モックテスト
4. 負荷テスト

---

**更新日**: 2026-01-03
**責任者**: AI Agent
