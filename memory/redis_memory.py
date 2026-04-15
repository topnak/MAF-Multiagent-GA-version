# ─────────────────────────────────────────────────────────────────────────────
# Redis Memory Provider
# ─────────────────────────────────────────────────────────────────────────────
# Redis-based implementation of the memory provider.
# Provides fast, scalable storage for conversation history and context.
# Works with any Redis deployment: local, AWS ElastiCache, Azure Redis, etc.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from .memory_provider import MemoryEntry, MemoryProvider
from config import get_settings

# Configure module logger
logger = logging.getLogger(__name__)


class RedisMemoryProvider(MemoryProvider):
    """
    Redis-based memory provider for MAF agents.
    
    This provider uses Redis sorted sets and hashes to store memory entries.
    Each session has its own namespace in Redis, allowing for efficient
    retrieval of recent entries and simple cleanup.
    
    Data Structure:
        - memory:{session_id}:entries (sorted set) - entry keys ordered by timestamp
        - memory:{session_id}:data:{key} (hash) - entry data
    
    Cloud Agnostic:
        Works with any Redis-compatible service:
        - Local Redis
        - AWS ElastiCache
        - Azure Cache for Redis
        - GCP Memorystore
        - Self-hosted Redis clusters
    
    Usage:
        # Initialize with connection URL
        memory = RedisMemoryProvider(redis_url="redis://localhost:6379")
        await memory.connect()
        
        # Store entries
        await memory.store("session-123", entry)
        
        # Cleanup
        await memory.close()
    """
    
    # Redis key prefixes
    KEY_PREFIX = "memory"
    ENTRIES_SUFFIX = "entries"  # Sorted set
    DATA_SUFFIX = "data"       # Hash keys
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_password: Optional[str] = None,
        key_prefix: Optional[str] = None,
        default_ttl_seconds: Optional[int] = None,
    ):
        """
        Initialize Redis memory provider.
        
        Args:
            redis_url: Redis connection URL. If not provided, uses settings.
            redis_password: Redis password. If not provided, uses settings.
            key_prefix: Custom key prefix for namespacing
            default_ttl_seconds: Default TTL for entries (None = no expiry)
        """
        settings = get_settings()
        
        self.redis_url = redis_url or settings.redis_url
        self.redis_password = redis_password or settings.redis_password.get_secret_value()
        self.key_prefix = key_prefix or self.KEY_PREFIX
        self.default_ttl_seconds = default_ttl_seconds
        
        self._client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """
        Establish connection to Redis.
        
        Call this method before using the provider.
        """
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                password=self.redis_password if self.redis_password else None,
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
    
    async def close(self) -> None:
        """
        Close the Redis connection.
        
        Call this method when done using the provider.
        """
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")
    
    async def _ensure_connected(self) -> redis.Redis:
        """Ensure connection is established and return client."""
        if self._client is None:
            await self.connect()
        return self._client
    
    def _entries_key(self, session_id: str) -> str:
        """Generate Redis key for session's entry index."""
        return f"{self.key_prefix}:{session_id}:{self.ENTRIES_SUFFIX}"
    
    def _data_key(self, session_id: str, key: str) -> str:
        """Generate Redis key for entry data."""
        return f"{self.key_prefix}:{session_id}:{self.DATA_SUFFIX}:{key}"
    
    async def store(self, session_id: str, entry: MemoryEntry) -> None:
        """
        Store a memory entry in Redis.
        
        Uses a sorted set for ordering entries by timestamp and
        separate hash keys for entry data.
        
        Args:
            session_id: Session identifier
            entry: Memory entry to store
        """
        client = await self._ensure_connected()
        
        # Update timestamp
        entry.updated_at = datetime.now(timezone.utc)
        
        # Use timestamp as score for sorted set
        score = entry.updated_at.timestamp()
        
        # Store entry data as JSON
        data_key = self._data_key(session_id, entry.key)
        await client.set(data_key, entry.to_json())
        
        # Apply TTL if specified
        ttl = entry.ttl_seconds or self.default_ttl_seconds
        if ttl:
            await client.expire(data_key, ttl)
        
        # Add to sorted set index
        entries_key = self._entries_key(session_id)
        await client.zadd(entries_key, {entry.key: score})
        
        # Apply TTL to index as well
        if ttl:
            await client.expire(entries_key, ttl)
        
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
        client = await self._ensure_connected()
        
        data_key = self._data_key(session_id, key)
        data = await client.get(data_key)
        
        if data:
            return MemoryEntry.from_json(data)
        return None
    
    async def get_recent(
        self,
        session_id: str,
        limit: int = 10,
        entry_type: Optional[str] = None,
    ) -> list[MemoryEntry]:
        """
        Get the most recent memory entries.
        
        Uses Redis sorted set to efficiently retrieve entries in
        reverse chronological order.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of entries
            entry_type: Filter by entry type (optional)
            
        Returns:
            List of memory entries, most recent first
        """
        client = await self._ensure_connected()
        
        entries_key = self._entries_key(session_id)
        
        # Get keys in reverse order (most recent first)
        # Request more if filtering by type
        fetch_limit = limit * 3 if entry_type else limit
        keys = await client.zrevrange(entries_key, 0, fetch_limit - 1)
        
        entries = []
        for key in keys:
            entry = await self.get(session_id, key)
            if entry:
                if entry_type and entry.entry_type != entry_type:
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break
        
        return entries
    
    async def search(
        self,
        session_id: str,
        query: str,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search memory entries by content.
        
        Note: This is a simple substring search. For production,
        consider using Redis Search module or external search service.
        
        Args:
            session_id: Session identifier
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching memory entries
        """
        client = await self._ensure_connected()
        
        # Get all entry keys for the session
        entries_key = self._entries_key(session_id)
        all_keys = await client.zrange(entries_key, 0, -1)
        
        query_lower = query.lower()
        results = []
        
        for key in all_keys:
            entry = await self.get(session_id, key)
            if entry and query_lower in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        
        # Sort by recency (most recent first)
        results.sort(key=lambda e: e.updated_at, reverse=True)
        
        return results
    
    async def delete(self, session_id: str, key: str) -> bool:
        """
        Delete a specific memory entry.
        
        Args:
            session_id: Session identifier
            key: Entry key to delete
            
        Returns:
            True if deleted, False if not found
        """
        client = await self._ensure_connected()
        
        # Delete from data store
        data_key = self._data_key(session_id, key)
        deleted = await client.delete(data_key)
        
        # Remove from index
        entries_key = self._entries_key(session_id)
        await client.zrem(entries_key, key)
        
        return deleted > 0
    
    async def clear_session(self, session_id: str) -> int:
        """
        Clear all memory entries for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of entries deleted
        """
        client = await self._ensure_connected()
        
        entries_key = self._entries_key(session_id)
        
        # Get all entry keys
        keys = await client.zrange(entries_key, 0, -1)
        
        # Delete all data keys
        count = 0
        for key in keys:
            data_key = self._data_key(session_id, key)
            deleted = await client.delete(data_key)
            count += deleted
        
        # Delete the index
        await client.delete(entries_key)
        
        logger.info(f"Cleared {count} entries for session {session_id}")
        return count
    
    async def get_session_ids(self, pattern: str = "*") -> list[str]:
        """
        Get all session IDs matching a pattern.
        
        Args:
            pattern: Glob pattern for matching session IDs
            
        Returns:
            List of matching session IDs
        """
        client = await self._ensure_connected()
        
        # Scan for matching entry keys
        search_pattern = f"{self.key_prefix}:{pattern}:{self.ENTRIES_SUFFIX}"
        
        session_ids = set()
        async for key in client.scan_iter(match=search_pattern):
            # Extract session ID from key
            parts = key.split(":")
            if len(parts) >= 3:
                session_ids.add(parts[1])
        
        return list(session_ids)
    
    async def get_stats(self, session_id: str) -> dict:
        """
        Get statistics for a session's memory.
        
        Args:
            session_id: Session identifier
            
        Returns:
            dict with entry count, oldest entry, newest entry
        """
        client = await self._ensure_connected()
        
        entries_key = self._entries_key(session_id)
        
        count = await client.zcard(entries_key)
        
        # Get oldest and newest
        oldest = await client.zrange(entries_key, 0, 0, withscores=True)
        newest = await client.zrevrange(entries_key, 0, 0, withscores=True)
        
        return {
            "session_id": session_id,
            "entry_count": count,
            "oldest_timestamp": datetime.fromtimestamp(oldest[0][1], tz=timezone.utc).isoformat() if oldest else None,
            "newest_timestamp": datetime.fromtimestamp(newest[0][1], tz=timezone.utc).isoformat() if newest else None,
        }
