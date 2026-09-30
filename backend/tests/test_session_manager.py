"""Tests for per-visitor session management."""
from __future__ import annotations

import pytest

from app.services.session_manager import InvalidSessionIdError, SessionManager
from tests.conftest import FakeEmbeddingService

A = "session-aaaaaaaaaaaaaaaa"
B = "session-bbbbbbbbbbbbbbbb"
C = "session-cccccccccccccccc"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_manager(clock, ttl=60, max_sessions=2):
    return SessionManager(
        embedding_service=FakeEmbeddingService(), ttl_seconds=ttl, max_sessions=max_sessions, clock=clock
    )


class TestSessionManager:
    def test_same_id_returns_same_service(self):
        manager = make_manager(FakeClock())
        assert manager.get(A) is manager.get(A)

    def test_different_ids_get_isolated_services(self):
        manager = make_manager(FakeClock())
        assert manager.get(A) is not manager.get(B)
        assert manager.get(A).vector_store is not manager.get(B).vector_store

    def test_sessions_never_persist_to_disk(self):
        assert make_manager(FakeClock()).get(A).persist is False

    @pytest.mark.parametrize("bad", ["", "short", "has spaces in it 1234567", "../../etc/passwd-xx", "x" * 65])
    def test_invalid_ids_are_rejected(self, bad):
        with pytest.raises(InvalidSessionIdError):
            make_manager(FakeClock()).get(bad)

    def test_idle_sessions_expire(self):
        clock = FakeClock()
        manager = make_manager(clock, ttl=60)
        first = manager.get(A)
        clock.now = 61
        assert manager.get(A) is not first  # expired -> fresh, empty session

    def test_activity_keeps_a_session_alive(self):
        clock = FakeClock()
        manager = make_manager(clock, ttl=60)
        first = manager.get(A)
        clock.now = 50
        manager.get(A)
        clock.now = 100  # 50s since last use, within TTL
        assert manager.get(A) is first

    def test_least_recently_used_session_is_evicted_at_capacity(self):
        clock = FakeClock()
        manager = make_manager(clock, max_sessions=2)
        a = manager.get(A)
        clock.now = 1
        manager.get(B)
        clock.now = 2
        manager.get(A)  # A is now more recent than B
        clock.now = 3
        manager.get(C)  # evicts B
        assert manager.active_sessions() == 2
        assert manager.get(A) is a
