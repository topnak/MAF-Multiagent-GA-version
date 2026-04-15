# ─────────────────────────────────────────────────────────────────────────────
# File-Based Checkpoint Store
# ─────────────────────────────────────────────────────────────────────────────
# Simple file-based implementation for local development and testing.
# Each checkpoint is stored as a JSON file.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

import aiofiles

from .checkpoint_store import CheckpointData, CheckpointStore

# Configure module logger
logger = logging.getLogger(__name__)


class FileCheckpointStore(CheckpointStore):
    """
    File-based checkpoint store for development and testing.
    
    Stores each checkpoint as a JSON file in a specified directory.
    Simple and portable, but not recommended for production with
    multiple instances.
    
    Usage:
        store = FileCheckpointStore("./checkpoints")
        
        await store.save(checkpoint)
        checkpoint = await store.load("session-123")
    """
    
    def __init__(self, directory: str = "./checkpoints"):
        """
        Initialize file checkpoint store.
        
        Args:
            directory: Directory to store checkpoint files
        """
        self.directory = Path(directory)
        
        # Create directory if it doesn't exist
        self.directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"File checkpoint store initialized at {self.directory.absolute()}")
    
    def _get_filepath(self, session_id: str) -> Path:
        """Get the file path for a session's checkpoint."""
        # Sanitize session ID for filesystem
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return self.directory / f"{safe_id}.checkpoint.json"
    
    async def save(self, checkpoint: CheckpointData) -> None:
        """
        Save a checkpoint to a JSON file.
        
        Args:
            checkpoint: Checkpoint data to save
        """
        filepath = self._get_filepath(checkpoint.session_id)
        
        async with aiofiles.open(filepath, "w") as f:
            await f.write(checkpoint.to_json())
        
        logger.debug(f"Saved checkpoint for session {checkpoint.session_id}")
    
    async def load(self, session_id: str) -> Optional[CheckpointData]:
        """
        Load a checkpoint from a JSON file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            CheckpointData if found, None otherwise
        """
        filepath = self._get_filepath(session_id)
        
        if not filepath.exists():
            return None
        
        try:
            async with aiofiles.open(filepath, "r") as f:
                content = await f.read()
            
            return CheckpointData.from_json(content)
        except Exception as e:
            logger.error(f"Failed to load checkpoint for {session_id}: {e}")
            return None
    
    async def delete(self, session_id: str) -> bool:
        """
        Delete a checkpoint file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        filepath = self._get_filepath(session_id)
        
        if filepath.exists():
            os.remove(filepath)
            logger.debug(f"Deleted checkpoint for session {session_id}")
            return True
        return False
    
    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """
        List all session IDs with checkpoints.
        
        Args:
            pattern: Glob pattern for filtering
            
        Returns:
            List of session IDs
        """
        sessions = []
        
        for filepath in self.directory.glob("*.checkpoint.json"):
            # Extract session ID from filename
            session_id = filepath.stem.replace(".checkpoint", "")
            
            if fnmatch(session_id, pattern):
                sessions.append(session_id)
        
        return sessions
    
    async def exists(self, session_id: str) -> bool:
        """
        Check if a checkpoint file exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if checkpoint exists
        """
        filepath = self._get_filepath(session_id)
        return filepath.exists()
    
    def get_directory_size(self) -> int:
        """
        Get total size of all checkpoint files.
        
        Returns:
            Total size in bytes
        """
        total = 0
        for filepath in self.directory.glob("*.checkpoint.json"):
            total += filepath.stat().st_size
        return total
    
    async def cleanup_old(self, max_age_hours: int = 24) -> int:
        """
        Delete checkpoints older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of checkpoints deleted
        """
        from datetime import datetime, timezone, timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        deleted = 0
        
        for filepath in self.directory.glob("*.checkpoint.json"):
            try:
                async with aiofiles.open(filepath, "r") as f:
                    content = await f.read()
                
                checkpoint = CheckpointData.from_json(content)
                
                if checkpoint.updated_at < cutoff:
                    os.remove(filepath)
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to check/delete {filepath}: {e}")
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old checkpoints")
        
        return deleted
