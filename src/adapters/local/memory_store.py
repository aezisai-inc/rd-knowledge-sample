"""
ローカル Memory アダプタ

SQLite + In-memory / Redis による MemoryStore Protocol 実装。
本番環境では AgentCore Memory を使用。

Usage:
    # SQLite モード（永続化）
    memory = LocalMemoryStore(
        mode="sqlite",
        db_path="./memory.db"
    )
    
    # Redis モード（高速アクセス）
    memory = LocalMemoryStore(
        mode="redis",
        redis_url="redis://localhost:6379"
    )
    
    # イベント保存
    memory.create_event([
        MemoryEvent(actor_id="user-1", session_id="sess-1", role="USER", content="Hello")
    ])
    
    # メモリ検索
    records = memory.retrieve_records(actor_id="user-1", query="greeting")
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ...interfaces import MemoryEvent, MemoryRecord

logger = logging.getLogger(__name__)


class LocalMemoryStore:
    """
    ローカル MemoryStore 実装

    モード:
    - "memory": In-memory 実装（テスト用）
    - "sqlite": SQLite による永続化
    - "redis": Redis による高速アクセス
    """

    def __init__(
        self,
        mode: str = "memory",
        db_path: str = "./memory.db",
        redis_url: str = "redis://localhost:6379",
    ):
        """
        Args:
            mode: "memory", "sqlite", または "redis"
            db_path: SQLite データベースパス
            redis_url: Redis 接続URL
        """
        self.mode = mode
        self.db_path = db_path
        self.redis_url = redis_url

        # In-memory ストア
        self._events: list[dict[str, Any]] = []
        self._records: dict[str, list[MemoryRecord]] = {}  # actor_id -> records

        # SQLite / Redis クライアント
        self._sqlite_conn: sqlite3.Connection | None = None
        self._redis_client = None

        if mode == "sqlite":
            self._init_sqlite()
        elif mode == "redis":
            self._init_redis()
        else:
            logger.info("LocalMemoryStore initialized in memory mode")

    def _init_sqlite(self) -> None:
        """SQLite 初期化"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._sqlite_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row

            # テーブル作成
            self._sqlite_conn.executescript("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    score REAL DEFAULT 0,
                    metadata TEXT,
                    embedding TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_actor ON memory_events(actor_id);
                CREATE INDEX IF NOT EXISTS idx_events_session ON memory_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_records_actor ON memory_records(actor_id);
                CREATE INDEX IF NOT EXISTS idx_records_type ON memory_records(memory_type);
            """)
            self._sqlite_conn.commit()
            logger.info(f"LocalMemoryStore initialized with SQLite ({self.db_path})")

        except Exception as e:
            logger.error(f"SQLite initialization failed: {e}")
            self.mode = "memory"

    def _init_redis(self) -> None:
        """Redis 初期化"""
        try:
            import redis

            self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self._redis_client.ping()
            logger.info(f"LocalMemoryStore initialized with Redis ({self.redis_url})")

        except ImportError:
            logger.warning("redis package not installed, falling back to memory mode")
            self.mode = "memory"
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to memory mode")
            self.mode = "memory"

    def create_event(
        self,
        events: list[MemoryEvent],
    ) -> str:
        """イベント保存（Short-term Memory）"""
        event_ids = []

        for event in events:
            event_id = str(uuid.uuid4())
            event_data = {
                "id": event_id,
                "actor_id": event.actor_id,
                "session_id": event.session_id,
                "role": event.role,
                "content": event.content,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata,
            }

            if self.mode == "sqlite" and self._sqlite_conn:
                self._save_event_sqlite(event_data)
            elif self.mode == "redis" and self._redis_client:
                self._save_event_redis(event_data)
            else:
                self._events.append(event_data)

            event_ids.append(event_id)

            # セマンティックメモリへの昇格チェック
            self._maybe_promote_to_semantic(event)

        logger.debug(f"Created {len(events)} events")
        return ",".join(event_ids)

    def _save_event_sqlite(self, event_data: dict[str, Any]) -> None:
        """SQLite にイベント保存"""
        self._sqlite_conn.execute(
            """
            INSERT INTO memory_events (id, actor_id, session_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_data["id"],
                event_data["actor_id"],
                event_data["session_id"],
                event_data["role"],
                event_data["content"],
                event_data["timestamp"],
                json.dumps(event_data["metadata"]),
            ),
        )
        self._sqlite_conn.commit()

    def _save_event_redis(self, event_data: dict[str, Any]) -> None:
        """Redis にイベント保存"""
        key = f"event:{event_data['actor_id']}:{event_data['session_id']}:{event_data['id']}"
        self._redis_client.hset(key, mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in event_data.items()
        })
        # セッション別インデックス
        self._redis_client.rpush(
            f"session:{event_data['actor_id']}:{event_data['session_id']}",
            event_data["id"]
        )
        # TTL 設定（24時間）
        self._redis_client.expire(key, 86400)

    def retrieve_records(
        self,
        actor_id: str,
        query: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> list[MemoryRecord]:
        """メモリ検索（セマンティック検索）"""
        if self.mode == "sqlite" and self._sqlite_conn:
            return self._retrieve_sqlite(actor_id, query, limit, memory_types)
        elif self.mode == "redis" and self._redis_client:
            return self._retrieve_redis(actor_id, query, limit, memory_types)
        return self._retrieve_memory(actor_id, query, limit, memory_types)

    def _retrieve_memory(
        self,
        actor_id: str,
        query: str,
        limit: int,
        memory_types: list[str] | None,
    ) -> list[MemoryRecord]:
        """In-memory モードの検索"""
        records = self._records.get(actor_id, [])
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for record in records:
            # メモリタイプフィルタ
            if memory_types and record.memory_type not in memory_types:
                continue

            # 簡易スコアリング
            content_lower = record.content.lower()
            content_words = set(content_lower.split())
            match_count = len(query_words & content_words)

            if match_count > 0:
                score = match_count / len(query_words)
                results.append(
                    MemoryRecord(
                        record_id=record.record_id,
                        content=record.content,
                        memory_type=record.memory_type,
                        timestamp=record.timestamp,
                        score=score,
                        metadata=record.metadata,
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _retrieve_sqlite(
        self,
        actor_id: str,
        query: str,
        limit: int,
        memory_types: list[str] | None,
    ) -> list[MemoryRecord]:
        """SQLite モードの検索"""
        type_filter = ""
        params: list[Any] = [actor_id, f"%{query}%"]

        if memory_types:
            placeholders = ",".join(["?" for _ in memory_types])
            type_filter = f"AND memory_type IN ({placeholders})"
            params.extend(memory_types)

        params.append(limit)

        cursor = self._sqlite_conn.execute(
            f"""
            SELECT id, actor_id, content, memory_type, timestamp, score, metadata
            FROM memory_records
            WHERE actor_id = ? AND content LIKE ? {type_filter}
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            params,
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                MemoryRecord(
                    record_id=row["id"],
                    content=row["content"],
                    memory_type=row["memory_type"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    score=row["score"] or 0.0,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )

        return results

    def _retrieve_redis(
        self,
        actor_id: str,
        query: str,
        limit: int,
        memory_types: list[str] | None,
    ) -> list[MemoryRecord]:
        """Redis モードの検索（簡易実装）"""
        pattern = f"record:{actor_id}:*"
        keys = self._redis_client.keys(pattern)
        query_lower = query.lower()

        results = []
        for key in keys:
            data = self._redis_client.hgetall(key)
            if not data:
                continue

            # メモリタイプフィルタ
            memory_type = data.get("memory_type", "")
            if memory_types and memory_type not in memory_types:
                continue

            content = data.get("content", "")
            if query_lower in content.lower():
                results.append(
                    MemoryRecord(
                        record_id=data.get("id", ""),
                        content=content,
                        memory_type=memory_type,
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                        score=float(data.get("score", 0)),
                        metadata=json.loads(data.get("metadata", "{}")),
                    )
                )

        return results[:limit]

    def get_session_history(
        self,
        actor_id: str,
        session_id: str,
        limit: int = 50,
    ) -> list[MemoryEvent]:
        """セッション履歴取得"""
        if self.mode == "sqlite" and self._sqlite_conn:
            return self._get_session_sqlite(actor_id, session_id, limit)
        elif self.mode == "redis" and self._redis_client:
            return self._get_session_redis(actor_id, session_id, limit)
        return self._get_session_memory(actor_id, session_id, limit)

    def _get_session_memory(
        self,
        actor_id: str,
        session_id: str,
        limit: int,
    ) -> list[MemoryEvent]:
        """In-memory モードのセッション取得"""
        events = [
            e for e in self._events
            if e["actor_id"] == actor_id and e["session_id"] == session_id
        ]
        events.sort(key=lambda x: x["timestamp"])

        return [
            MemoryEvent(
                actor_id=e["actor_id"],
                session_id=e["session_id"],
                role=e["role"],
                content=e["content"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                metadata=e.get("metadata", {}),
            )
            for e in events[-limit:]
        ]

    def _get_session_sqlite(
        self,
        actor_id: str,
        session_id: str,
        limit: int,
    ) -> list[MemoryEvent]:
        """SQLite モードのセッション取得"""
        cursor = self._sqlite_conn.execute(
            """
            SELECT actor_id, session_id, role, content, timestamp, metadata
            FROM memory_events
            WHERE actor_id = ? AND session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (actor_id, session_id, limit),
        )

        events = []
        for row in cursor.fetchall():
            events.append(
                MemoryEvent(
                    actor_id=row["actor_id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
            )

        events.reverse()  # 時系列順に
        return events

    def _get_session_redis(
        self,
        actor_id: str,
        session_id: str,
        limit: int,
    ) -> list[MemoryEvent]:
        """Redis モードのセッション取得"""
        key = f"session:{actor_id}:{session_id}"
        event_ids = self._redis_client.lrange(key, -limit, -1)

        events = []
        for event_id in event_ids:
            event_key = f"event:{actor_id}:{session_id}:{event_id}"
            data = self._redis_client.hgetall(event_key)
            if data:
                events.append(
                    MemoryEvent(
                        actor_id=data.get("actor_id", ""),
                        session_id=data.get("session_id", ""),
                        role=data.get("role", ""),
                        content=data.get("content", ""),
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                        metadata=json.loads(data.get("metadata", "{}")),
                    )
                )

        return events

    def delete_actor_memory(
        self,
        actor_id: str,
    ) -> bool:
        """アクターのメモリ全削除"""
        try:
            if self.mode == "sqlite" and self._sqlite_conn:
                self._sqlite_conn.execute(
                    "DELETE FROM memory_events WHERE actor_id = ?", (actor_id,)
                )
                self._sqlite_conn.execute(
                    "DELETE FROM memory_records WHERE actor_id = ?", (actor_id,)
                )
                self._sqlite_conn.commit()

            elif self.mode == "redis" and self._redis_client:
                # イベントキー削除
                for key in self._redis_client.keys(f"event:{actor_id}:*"):
                    self._redis_client.delete(key)
                # セッションキー削除
                for key in self._redis_client.keys(f"session:{actor_id}:*"):
                    self._redis_client.delete(key)
                # レコードキー削除
                for key in self._redis_client.keys(f"record:{actor_id}:*"):
                    self._redis_client.delete(key)

            else:
                self._events = [e for e in self._events if e["actor_id"] != actor_id]
                self._records.pop(actor_id, None)

            logger.info(f"Deleted all memory for actor: {actor_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory for actor {actor_id}: {e}")
            return False

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _maybe_promote_to_semantic(self, event: MemoryEvent) -> None:
        """イベントをセマンティックメモリに昇格（簡易実装）"""
        # 重要なイベントをセマンティックメモリに保存
        # 実際の AgentCore Memory では ML モデルで判定
        if len(event.content) > 100:  # 長いメッセージは知識として保存
            record = MemoryRecord(
                record_id=str(uuid.uuid4()),
                content=event.content,
                memory_type="semantic",
                timestamp=event.timestamp,
                score=0.5,
                metadata={
                    "source": "event",
                    "session_id": event.session_id,
                    **event.metadata,
                },
            )
            self._save_record(event.actor_id, record)

    def _save_record(self, actor_id: str, record: MemoryRecord) -> None:
        """メモリレコード保存"""
        if self.mode == "sqlite" and self._sqlite_conn:
            self._sqlite_conn.execute(
                """
                INSERT INTO memory_records (id, actor_id, content, memory_type, timestamp, score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    actor_id,
                    record.content,
                    record.memory_type,
                    record.timestamp.isoformat(),
                    record.score,
                    json.dumps(record.metadata),
                ),
            )
            self._sqlite_conn.commit()

        elif self.mode == "redis" and self._redis_client:
            key = f"record:{actor_id}:{record.record_id}"
            self._redis_client.hset(key, mapping={
                "id": record.record_id,
                "content": record.content,
                "memory_type": record.memory_type,
                "timestamp": record.timestamp.isoformat(),
                "score": str(record.score),
                "metadata": json.dumps(record.metadata),
            })

        else:
            if actor_id not in self._records:
                self._records[actor_id] = []
            self._records[actor_id].append(record)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """統計情報取得"""
        if self.mode == "sqlite" and self._sqlite_conn:
            event_count = self._sqlite_conn.execute(
                "SELECT COUNT(*) FROM memory_events"
            ).fetchone()[0]
            record_count = self._sqlite_conn.execute(
                "SELECT COUNT(*) FROM memory_records"
            ).fetchone()[0]
        elif self.mode == "redis" and self._redis_client:
            event_count = len(self._redis_client.keys("event:*"))
            record_count = len(self._redis_client.keys("record:*"))
        else:
            event_count = len(self._events)
            record_count = sum(len(records) for records in self._records.values())

        return {
            "mode": self.mode,
            "event_count": event_count,
            "record_count": record_count,
        }

    def close(self) -> None:
        """接続クローズ"""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
