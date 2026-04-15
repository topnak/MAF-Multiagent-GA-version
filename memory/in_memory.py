# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Provider
# ─────────────────────────────────────────────────────────────────────────────
# Simple in-memory implementation for testing and development.
# Data is lost when the application restarts.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from collections import defaultdict
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Optional

from .memory_provider import MemoryEntry, MemoryProvider

# Configure module logger
logger = logging.getLogger(__name__)


class InMemoryProvider(MemoryProvider):
    """
    In-memory implementation of the memory provider.
    
    This provider stores all data in Python dictionaries. It's useful for:
    - Unit testing
    - Local development
    - Prototyping
    
    Note: Data is NOT persisted and will be lost when the application stops.
    For production, use RedisMemoryProvider or another persistent backend.
    
    Usage:
        memory = InMemoryProvider()
        await memory.store("session-123", entry)
        entries = await memory.get_recent("session-123")
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        # Structure: {session_id: {key: MemoryEntry}}
        self._storage: dict[str, dict[str, MemoryEntry]] = defaultdict(dict)
    
    async def store(self, session_id: str, entry: MemoryEntry) -> None:
        """
        Store a memory entry.
        
        Args:
            session_id: Session identifier
            entry: Memory entry to store
        """
        # Update timestamp
        entry.updated_at = datetime.now(timezone.utc)
        
        # Store entry (make a copy to prevent external modifications)
        self._storage[session_id][entry.key] = MemoryEntry(
            key=entry.key,
            content=entry.content,
            metadata=dict(entry.metadata),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            ttl_seconds=entry.ttl_seconds,
            entry_type=entry.entry_type,
        )
        
        logger.debug(f"Stored entry {entry.key} in session {session_id}")
    
    async def get(self, session_id: str, key: str) -> Optional[MemoryEntry]:
        """
        Get a specific memory entry by key.
        
        Args:
            session_id: Session identifier
            key: Entry key
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        session_data = self._storage.get(session_id, {})
        entry = session_data.get(key)
        
        if entry:
            # Check TTL
            if entry.ttl_seconds:
                age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                if age > entry.ttl_seconds:
                    # Entry has expired
                    await self.delete(session_id, key)
                    return None
        
        return entry
    
    async def get_recent(
        self,
        session_id: str,
        limit: int = 10,
        entry_type: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """
        Get the most recent memory entries.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of entries
            entry_type: Filter by entry type (optional)
            
        Returns:
            List of memory entries, most recent first
        """
        session_data = self._storage.get(session_id, {})
        
        # Get all entries
        entries = list(session_data.values())
        
        # Filter by type if specified
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        
        # Filter expired entries
        now = datetime.now(timezone.utc)
        valid_entries = []
        for entry in entries:
            if entry.ttl_seconds:
                age = (now - entry.created_at).total_seconds()
                if age > entry.ttl_seconds:
                    continue
            valid_entries.append(entry)
        
        # Sort by updated_at descending (most recent first)
        valid_entries.sort(key=lambda e: e.updated_at, reverse=True)
        
        return valid_entries[:limit]
    
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
            query: Search query (case-insensitive substring match)
            limit: Maximum number of results
            
        Returns:
            List of matching memory entries
        """
        session_data = self._storage.get(session_id, {})
        query_lower = query.lower()
        
        # Search by substring
        results = [
            entry for entry in session_data.values()
            if query_lower in entry.content.lower()
        ]
        
        # Sort by recency
        results.sort(key=lambda e: e.updated_at, reverse=True)
        
        return results[:limit]
    
    async def delete(self, session_id: str, key: str) -> bool:
        """
        Delete a specific memory entry.
        
        Args:
            session_id: Session identifier
            key: Entry key to delete
            
        Returns:
            True if deleted, False if not found
        """
        session_data = self._storage.get(session_id, {})
        
        if key in session_data:
            del session_data[key]
            return True
        return False
    
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all memory entries for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of entries deleted
        """
        if session_id in self._storage:
            count = len(self._storage[session_id])
            del self._storage[session_id]
            logger.info(f"Cleared {count} entries for session {session_id}")
            return count
        return 0
    
    async def get_session_ids(self, pattern: str = "*") -> list[str]:
        """
        Get all session IDs matching a pattern.
        
        Args:
            pattern: Glob pattern for matching session IDs
            
        Returns:
            List of matching session IDs
        """
        return [
            session_id for session_id in self._storage.keys()
            if fnmatch(session_id, pattern)
        ]
    
    def get_total_entries(self) -> int:
        """
        Get total number of entries across all sessions.
        
        Returns:
            Total entry count
        """
        return sum(len(entries) for entries in self._storage.values())
    
    def clear_all(self) -> None:
        """Clear all sessions and entries."""
        self._storage.clear()
        logger.info("Cleared all in-memory storage")
