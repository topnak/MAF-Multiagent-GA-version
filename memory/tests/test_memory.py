# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests for Memory Module
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from datetime import datetime, timezone, timedelta

from memory.memory_provider import MemoryEntry
from memory.in_memory import InMemoryProvider


class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""
    
    def test_create_entry(self):
        """Test creating a memory entry."""
        entry = MemoryEntry(
            key="test-1",
            content="Hello, world!",
            metadata={"role": "user"},
            entry_type="message",
        )
        
        assert entry.key == "test-1"
        assert entry.content == "Hello, world!"
        assert entry.metadata["role"] == "user"
        assert entry.entry_type == "message"
    
    def test_entry_to_dict(self):
        """Test serializing entry to dictionary."""
        entry = MemoryEntry(
            key="test-2",
            content="Test content",
            metadata={"key": "value"},
        )
        
        data = entry.to_dict()
        
        assert data["key"] == "test-2"
        assert data["content"] == "Test content"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_entry_from_dict(self):
        """Test deserializing entry from dictionary."""
        data = {
            "key": "test-3",
            "content": "From dict",
            "metadata": {"source": "test"},
            "created_at": "2024-01-15T12:00:00+00:00",
            "updated_at": "2024-01-15T12:00:00+00:00",
            "entry_type": "context",
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.key == "test-3"
        assert entry.content == "From dict"
        assert entry.entry_type == "context"
    
    def test_entry_json_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = MemoryEntry(
            key="test-4",
            content="JSON test",
            metadata={"nested": {"value": 123}},
        )
        
        json_str = original.to_json()
        restored = MemoryEntry.from_json(json_str)
        
        assert restored.key == original.key
        assert restored.content == original.content
        assert restored.metadata == original.metadata


class TestInMemoryProvider:
    """Tests for InMemoryProvider."""
    
    @pytest.fixture
    def memory(self):
        """Create in-memory provider for testing."""
        return InMemoryProvider()
    
    @pytest.mark.asyncio
    async def test_store_and_get(self, memory):
        """Test storing and retrieving an entry."""
        entry = MemoryEntry(
            key="msg-1",
            content="Hello!",
            metadata={"role": "user"},
        )
        
        await memory.store("session-1", entry)
        retrieved = await memory.get("session-1", "msg-1")
        
        assert retrieved is not None
        assert retrieved.content == "Hello!"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, memory):
        """Test getting a non-existent entry returns None."""
        result = await memory.get("session-1", "nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_recent(self, memory):
        """Test retrieving recent entries in order."""
        # Store entries with slight time gaps
        for i in range(5):
            entry = MemoryEntry(
                key=f"msg-{i}",
                content=f"Message {i}",
            )
            await memory.store("session-1", entry)
        
        recent = await memory.get_recent("session-1", limit=3)
        
        assert len(recent) == 3
        # Most recent should be first
        assert recent[0].key == "msg-4"
        assert recent[2].key == "msg-2"
    
    @pytest.mark.asyncio
    async def test_get_recent_with_type_filter(self, memory):
        """Test filtering recent entries by type."""
        # Store mixed entry types
        await memory.store("session-1", MemoryEntry(
            key="msg-1", content="Message", entry_type="message"
        ))
        await memory.store("session-1", MemoryEntry(
            key="ctx-1", content="Context", entry_type="context"
        ))
        await memory.store("session-1", MemoryEntry(
            key="msg-2", content="Message 2", entry_type="message"
        ))
        
        messages = await memory.get_recent("session-1", entry_type="message")
        
        assert len(messages) == 2
        assert all(e.entry_type == "message" for e in messages)
    
    @pytest.mark.asyncio
    async def test_search(self, memory):
        """Test searching entries by content."""
        await memory.store("session-1", MemoryEntry(
            key="msg-1", content="The weather is sunny"
        ))
        await memory.store("session-1", MemoryEntry(
            key="msg-2", content="I like pizza"
        ))
        await memory.store("session-1", MemoryEntry(
            key="msg-3", content="Tomorrow's weather forecast"
        ))
        
        results = await memory.search("session-1", "weather")
        
        assert len(results) == 2
        assert all("weather" in r.content.lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """Test deleting an entry."""
        await memory.store("session-1", MemoryEntry(
            key="to-delete", content="Delete me"
        ))
        
        deleted = await memory.delete("session-1", "to-delete")
        
        assert deleted is True
        assert await memory.get("session-1", "to-delete") is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, memory):
        """Test deleting non-existent entry returns False."""
        deleted = await memory.delete("session-1", "nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_clear_session(self, memory):
        """Test clearing all entries for a session."""
        # Store multiple entries
        for i in range(5):
            await memory.store("session-1", MemoryEntry(
                key=f"msg-{i}", content=f"Content {i}"
            ))
        
        count = await memory.clear_session("session-1")
        
        assert count == 5
        assert await memory.get_recent("session-1") == []
    
    @pytest.mark.asyncio
    async def test_get_session_ids(self, memory):
        """Test getting session IDs with pattern matching."""
        await memory.store("user-123-session", MemoryEntry(key="a", content="A"))
        await memory.store("user-456-session", MemoryEntry(key="b", content="B"))
        await memory.store("admin-session", MemoryEntry(key="c", content="C"))
        
        user_sessions = await memory.get_session_ids("user-*")
        
        assert len(user_sessions) == 2
        assert "user-123-session" in user_sessions
        assert "user-456-session" in user_sessions
    
    @pytest.mark.asyncio
    async def test_store_message_convenience(self, memory):
        """Test the store_message convenience method."""
        entry = await memory.store_message(
            session_id="session-1",
            role="user",
            content="Hello agent!",
        )
        
        assert entry.entry_type == "message"
        assert entry.metadata["role"] == "user"
        
        retrieved = await memory.get("session-1", entry.key)
        assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, memory):
        """Test getting conversation history for LLM context."""
        await memory.store_message("session-1", "user", "Hello")
        await memory.store_message("session-1", "assistant", "Hi there!")
        await memory.store_message("session-1", "user", "How are you?")
        
        history = await memory.get_conversation_history("session-1")
        
        assert len(history) == 3
        # Should be in chronological order (oldest first)
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[-1]["content"] == "How are you?"
    
    @pytest.mark.asyncio
    async def test_ttl_expiry(self, memory):
        """Test that TTL causes entries to expire."""
        # Store entry with very short TTL
        entry = MemoryEntry(
            key="expires-soon",
            content="I will expire",
            ttl_seconds=0,  # Immediately expired
            created_at=datetime.now(timezone.utc) - timedelta(seconds=1),  # Created in past
        )
        await memory.store("session-1", entry)
        
        # Should not be retrievable
        result = await memory.get("session-1", "expires-soon")
        assert result is None
    
    def test_get_total_entries(self, memory):
        """Test counting total entries."""
        # Use sync to add entries directly for testing
        memory._storage["session-1"]["a"] = MemoryEntry(key="a", content="A")
        memory._storage["session-1"]["b"] = MemoryEntry(key="b", content="B")
        memory._storage["session-2"]["c"] = MemoryEntry(key="c", content="C")
        
        assert memory.get_total_entries() == 3
    
    def test_clear_all(self, memory):
        """Test clearing all storage."""
        memory._storage["session-1"]["a"] = MemoryEntry(key="a", content="A")
        memory._storage["session-2"]["b"] = MemoryEntry(key="b", content="B")
        
        memory.clear_all()
        
        assert memory.get_total_entries() == 0
