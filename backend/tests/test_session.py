"""
Tests for session management and storage.

These tests verify the in-memory session store works correctly,
including LRU eviction and session lifecycle.
"""

import time

import pytest

from app.models.session import InMemorySessionStore, Session


class TestSession:
    """Tests for the Session dataclass."""

    def test_session_creation(self, minimal_user_input):
        """Session should be created with correct defaults."""
        session = Session(
            session_id="test-123",
            user_input=minimal_user_input,
        )

        assert session.session_id == "test-123"
        assert session.user_input == minimal_user_input
        assert session.segments == []
        assert session.narrative_context == ""
        assert session.is_generating is False
        assert session.arc_outline is None
        assert session.owner_id is None
        assert session.is_public is False

    def test_is_generating_stale_when_not_generating(self, minimal_user_input):
        """is_generating_stale should be False when not generating."""
        session = Session(
            session_id="test-123",
            user_input=minimal_user_input,
            is_generating=False,
        )
        assert session.is_generating_stale is False

    def test_is_generating_stale_when_recently_started(self, minimal_user_input):
        """is_generating_stale should be False when recently started."""
        session = Session(
            session_id="test-123",
            user_input=minimal_user_input,
            is_generating=True,
            generating_started_at=time.time(),
        )
        assert session.is_generating_stale is False

    def test_is_generating_stale_after_timeout(self, minimal_user_input):
        """is_generating_stale should be True after timeout."""
        session = Session(
            session_id="test-123",
            user_input=minimal_user_input,
            is_generating=True,
            generating_started_at=time.time() - 400,  # 400 seconds ago (> 300s timeout)
        )
        assert session.is_generating_stale is True


class TestInMemorySessionStore:
    """Tests for the InMemorySessionStore."""

    def test_create_session(self, session_store, minimal_user_input):
        """Should create and store a session."""
        session = session_store.create("test-123", minimal_user_input)

        assert session.session_id == "test-123"
        assert session.user_input == minimal_user_input
        assert session_store.exists("test-123")

    def test_get_existing_session(self, session_store, minimal_user_input):
        """Should retrieve an existing session."""
        session_store.create("test-123", minimal_user_input)

        retrieved = session_store.get("test-123")

        assert retrieved is not None
        assert retrieved.session_id == "test-123"

    def test_get_nonexistent_session(self, session_store):
        """Should return None for nonexistent session."""
        assert session_store.get("nonexistent") is None

    def test_exists_returns_true_for_existing(self, session_store, minimal_user_input):
        """exists() should return True for existing sessions."""
        session_store.create("test-123", minimal_user_input)
        assert session_store.exists("test-123") is True

    def test_exists_returns_false_for_nonexistent(self, session_store):
        """exists() should return False for nonexistent sessions."""
        assert session_store.exists("nonexistent") is False

    def test_update_session(self, session_store, minimal_user_input):
        """Should update session data."""
        session = session_store.create("test-123", minimal_user_input)
        session.narrative_context = "Updated context"
        session.is_generating = True

        session_store.update(session)
        retrieved = session_store.get("test-123")

        assert retrieved.narrative_context == "Updated context"
        assert retrieved.is_generating is True

    def test_count_returns_correct_number(self, session_store, minimal_user_input):
        """count() should return the number of sessions."""
        assert session_store.count() == 0

        session_store.create("test-1", minimal_user_input)
        assert session_store.count() == 1

        session_store.create("test-2", minimal_user_input)
        assert session_store.count() == 2

    def test_set_owner(self, session_store, minimal_user_input):
        """Should set the owner of a session."""
        session_store.create("test-123", minimal_user_input)

        result = session_store.set_owner("test-123", "user-456")

        assert result is True
        session = session_store.get("test-123")
        assert session.owner_id == "user-456"

    def test_set_owner_nonexistent_session(self, session_store):
        """set_owner should return False for nonexistent session."""
        result = session_store.set_owner("nonexistent", "user-456")
        assert result is False

    def test_list_by_owner(self, session_store, minimal_user_input):
        """Should list sessions owned by a user."""
        # Create sessions with different owners
        session_store.create("test-1", minimal_user_input)
        session_store.set_owner("test-1", "user-A")

        session_store.create("test-2", minimal_user_input)
        session_store.set_owner("test-2", "user-A")

        session_store.create("test-3", minimal_user_input)
        session_store.set_owner("test-3", "user-B")

        user_a_sessions = session_store.list_by_owner("user-A")
        user_b_sessions = session_store.list_by_owner("user-B")

        assert len(user_a_sessions) == 2
        assert len(user_b_sessions) == 1

    def test_list_by_owner_respects_limit(self, session_store, minimal_user_input):
        """list_by_owner should respect the limit parameter."""
        for i in range(5):
            session_store.create(f"test-{i}", minimal_user_input)
            session_store.set_owner(f"test-{i}", "user-A")

        sessions = session_store.list_by_owner("user-A", limit=3)
        assert len(sessions) == 3


class TestLRUEviction:
    """Tests for LRU eviction behavior."""

    def test_evicts_oldest_when_at_capacity(self, minimal_user_input):
        """Should evict oldest session when at capacity."""
        store = InMemorySessionStore(max_sessions=3)

        store.create("old-1", minimal_user_input)
        store.create("old-2", minimal_user_input)
        store.create("old-3", minimal_user_input)

        # This should trigger eviction of old-1
        store.create("new-4", minimal_user_input)

        assert store.count() == 3
        assert not store.exists("old-1")  # Evicted
        assert store.exists("old-2")
        assert store.exists("old-3")
        assert store.exists("new-4")

    def test_get_moves_to_end_of_lru(self, minimal_user_input):
        """Accessing a session should move it to end of LRU."""
        store = InMemorySessionStore(max_sessions=3)

        store.create("first", minimal_user_input)
        store.create("second", minimal_user_input)
        store.create("third", minimal_user_input)

        # Access "first" to move it to end
        store.get("first")

        # Add new session - should evict "second" (now oldest)
        store.create("fourth", minimal_user_input)

        assert store.exists("first")  # Still exists (was accessed)
        assert not store.exists("second")  # Evicted
        assert store.exists("third")
        assert store.exists("fourth")

    def test_does_not_evict_generating_sessions(self, minimal_user_input):
        """Should not evict sessions that are currently generating."""
        store = InMemorySessionStore(max_sessions=3)

        # Create first session and mark as generating
        session1 = store.create("generating-1", minimal_user_input)
        session1.is_generating = True
        store.update(session1)

        store.create("normal-2", minimal_user_input)
        store.create("normal-3", minimal_user_input)

        # This should evict normal-2, not generating-1
        store.create("new-4", minimal_user_input)

        assert store.exists("generating-1")  # Not evicted (generating)
        assert not store.exists("normal-2")  # Evicted
        assert store.exists("normal-3")
        assert store.exists("new-4")


class TestAppendSegment:
    """Tests for appending narrative segments."""

    def test_append_segment(self, session_store, minimal_user_input):
        """Should append a segment to the session."""
        from app.models.schemas import NarrativeSegment

        session_store.create("test-123", minimal_user_input)

        segment = NarrativeSegment(
            type="text",
            content="Test narrative content",
            trust_level="historical",
            sequence=1,
        )

        session_store.append_segment("test-123", segment)

        session = session_store.get("test-123")
        assert len(session.segments) == 1
        assert session.segments[0].content == "Test narrative content"

    def test_append_segment_is_idempotent(self, session_store, minimal_user_input):
        """Appending same segment twice should not duplicate."""
        from app.models.schemas import NarrativeSegment

        session_store.create("test-123", minimal_user_input)

        segment = NarrativeSegment(
            type="text",
            content="Test content",
            trust_level="cultural",
            sequence=1,
        )

        session_store.append_segment("test-123", segment)
        session_store.append_segment("test-123", segment)

        session = session_store.get("test-123")
        assert len(session.segments) == 1

    def test_append_multiple_segments(self, session_store, minimal_user_input):
        """Should append multiple segments with different sequences."""
        from app.models.schemas import NarrativeSegment

        session_store.create("test-123", minimal_user_input)

        for i in range(3):
            segment = NarrativeSegment(
                type="text",
                content=f"Segment {i}",
                trust_level="historical",
                sequence=i,
            )
            session_store.append_segment("test-123", segment)

        session = session_store.get("test-123")
        assert len(session.segments) == 3
