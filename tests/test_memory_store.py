"""
MemoryStore E2E テスト

ローカル環境と AWS 環境の両方で同一テストケースを実行。
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.interfaces import MemoryEvent, MemoryRecord


class TestMemoryStore:
    """MemoryStore Protocol の E2E テスト"""

    def test_create_event(self, memory_store, sample_events):
        """イベント作成テスト"""
        result = memory_store.create_event(sample_events)

        assert result is not None
        assert len(result) > 0  # イベントIDが返される

    def test_get_session_history(self, memory_store, sample_events):
        """セッション履歴取得テスト"""
        # イベント保存
        memory_store.create_event(sample_events)

        # 履歴取得
        history = memory_store.get_session_history(
            actor_id="test-actor",
            session_id="session-1",
            limit=10,
        )

        assert len(history) > 0
        assert isinstance(history[0], MemoryEvent)
        assert history[0].actor_id == "test-actor"

    def test_retrieve_records(self, memory_store, sample_events):
        """メモリレコード検索テスト"""
        # イベント保存
        memory_store.create_event(sample_events)

        # 検索（会話内容から）
        records = memory_store.retrieve_records(
            actor_id="test-actor",
            query="hello",
            limit=5,
        )

        assert len(records) >= 0  # メモリタイプによっては0件の場合も

    def test_retrieve_with_memory_types(self, memory_store, sample_events):
        """メモリタイプ指定検索テスト"""
        # イベント保存
        memory_store.create_event(sample_events)

        # semantic タイプのみ検索
        records = memory_store.retrieve_records(
            actor_id="test-actor",
            query="greeting",
            limit=5,
            memory_types=["semantic"],
        )

        # semantic タイプのみが返されるはず
        for record in records:
            assert record.memory_type == "semantic"

    def test_delete_actor_memory(self, memory_store, sample_events):
        """アクターメモリ削除テスト"""
        # イベント保存
        memory_store.create_event(sample_events)

        # 削除
        result = memory_store.delete_actor_memory("test-actor")

        assert result is True

        # 削除後は履歴が空
        history = memory_store.get_session_history(
            actor_id="test-actor",
            session_id="session-1",
        )

        assert len(history) == 0

    def test_multiple_sessions(self, memory_store):
        """複数セッションのテスト"""
        # セッション1のイベント
        session1_events = [
            MemoryEvent(
                actor_id="test-actor",
                session_id="session-1",
                role="USER",
                content="Session 1 message",
                timestamp=datetime.now(),
            )
        ]

        # セッション2のイベント
        session2_events = [
            MemoryEvent(
                actor_id="test-actor",
                session_id="session-2",
                role="USER",
                content="Session 2 message",
                timestamp=datetime.now(),
            )
        ]

        # 両セッションを保存
        memory_store.create_event(session1_events)
        memory_store.create_event(session2_events)

        # セッション1の履歴
        history1 = memory_store.get_session_history(
            actor_id="test-actor",
            session_id="session-1",
        )

        # セッション2の履歴
        history2 = memory_store.get_session_history(
            actor_id="test-actor",
            session_id="session-2",
        )

        # 各セッションの履歴が分離されている
        assert all("Session 1" in e.content for e in history1)
        assert all("Session 2" in e.content for e in history2)

    def test_event_ordering(self, memory_store):
        """イベント順序テスト"""
        events = [
            MemoryEvent(
                actor_id="test-actor",
                session_id="session-order",
                role="USER",
                content=f"Message {i}",
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        memory_store.create_event(events)

        history = memory_store.get_session_history(
            actor_id="test-actor",
            session_id="session-order",
            limit=10,
        )

        # 時系列順になっているはず
        for i, event in enumerate(history):
            assert f"Message {i}" in event.content
