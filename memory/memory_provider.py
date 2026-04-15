# ─────────────────────────────────────────────────────────────────────────────
# Memory Provider Abstraction
# ─────────────────────────────────────────────────────────────────────────────
# Defines the interface for memory providers in MAF 1.0 GA.
# Memory providers store conversation history and cross-session context.
# ─────────────────────────────────────────────────────────────────────────────

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class MemoryEntry:
    """
    Represents a single memory entry stored by the provider.
    
    Memory entries can store:
    - Conversation messages
    - User preferences
    - Cross-session context
    - Agent observations
    
    Attributes:
        key: Unique identifier for the entry
        content: The stored content (text or structured data)
        metadata: Additional metadata about the entry
        created_at: When the entry was created
        updated_at: When the entry was last updated
        ttl_seconds: Time-to-live in seconds (None = no expiry)
        entry_type: Type of entry (message, preference, context, observation)
    """
    key: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: Optional[int] = None
    entry_type: str = "message"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "key": self.key,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "entry_type": self.entry_type,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create entry from dictionary."""
        return cls(
            key=data["key"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
            ttl_seconds=data.get("ttl_seconds"),
            entry_type=data.get("entry_type", "message"),
        )
    
    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "MemoryEntry":
        """Create entry from JSON string."""
        return cls.from_dict(json.loads(json_str))


class MemoryProvider(ABC):
    """
    Abstract base class for memory providers.
    
    Memory providers handle storage and retrieval of conversation history
    and cross-session memory for agents. Implementations can use any
    backend: Redis, databases, file storage, etc.
    
    MAF 1.0 GA Pattern:
        The memory provider is attached to agents and orchestrations
        to enable persistent conversation history and context sharing.
    
    Usage:
        memory = RedisMemoryProvider(redis_url="redis://localhost:6379")
        
        # Store a message
        await memory.store(
            session_id="session-123",
            entry=MemoryEntry(key="msg-1", content="Hello!")
        )
        
        # Retrieve recent messages
        messages = await memory.get_recent(session_id="session-123", limit=10)
        
        # Search memory
        results = await memory.search(session_id="session-123", query="weather")
    """
    
    @abstractmethod
    async def store(self, session_id: str, entry: MemoryEntry) -> None:
        """
        Store a memory entry for a session.
        
        Args:
            session_id: Unique identifier for the session
            entry: Memory entry to store
        """
        pass
    
    @abstractmethod
    async def get(self, session_id: str, key: str) -> Optional[MemoryEntry]:
        """
        Get a specific memory entry by key.
        
        Args:
            session_id: Session identifier
            key: Entry key
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_recent(
        self,
        session_id: str,
        limit: int = 10,
        entry_type: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """
        Get the most recent memory entries for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of entries to return
            entry_type: Filter by entry type (optional)
            
        Returns:
            List of memory entries, most recent first
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search memory entries by content.
        
        Args:
            session_id: Session identifier
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching memory entries
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: str, key: str) -> bool:
        """
        Delete a specific memory entry.
        
        Args:
            session_id: Session identifier
            key: Entry key to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all memory entries for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of entries deleted
        """
        pass
    
    @abstractmethod
    async def get_session_ids(self, pattern: str = "*") -> list[str]:
        """
        Get all session IDs matching a pattern.
        
        Args:
            pattern: Glob pattern for matching session IDs
            
        Returns:
            List of matching session IDs
        """
        pass
    
    # ─────────────────────────────────────────────────────────────────────────
    # Convenience methods (with default implementations)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def store_message(
        self,
        session_id: str,
        role: str,
        content: str,
        key: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> MemoryEntry:
        """
        Convenience method to store a conversation message.
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            key: Optional entry key (auto-generated if not provided)
            metadata: Additional message metadata
            
        Returns:
            The stored memory entry
        """
        import uuid
        
        entry = MemoryEntry(
            key=key or f"msg-{uuid.uuid4().hex[:8]}",
            content=content,
            metadata={"role": role, **(metadata or {})},
            entry_type="message",
        )
        
        await self.store(session_id, entry)
        return entry
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, str]]:
        """
        Get conversation history in a format suitable for LLM context.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages
            
        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        entries = await self.get_recent(session_id, limit=limit, entry_type="message")
        
        # Reverse to get chronological order (oldest first)
        entries.reverse()
        
        return [
            {
                "role": entry.metadata.get("role", "user"),
                "content": entry.content,
            }
            for entry in entries
        ]
    
    async def store_context(
        self,
        session_id: str,
        key: str,
        content: str,
        metadata: Optional[dict] = None,
        ttl_seconds: Optional[int] = None,
    ) -> MemoryEntry:
        """
        Store cross-session context.
        
        Args:
            session_id: Session identifier
            key: Context key
            content: Context content
            metadata: Additional metadata
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            The stored memory entry
        """
        entry = MemoryEntry(
            key=key,
            content=content,
            metadata=metadata or {},
            entry_type="context",
            ttl_seconds=ttl_seconds,
        )
        
        await self.store(session_id, entry)
        return entry
