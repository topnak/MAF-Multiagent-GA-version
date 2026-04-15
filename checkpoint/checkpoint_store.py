# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint Store Abstraction
# ─────────────────────────────────────────────────────────────────────────────
# Defines the interface for checkpoint stores in MAF 1.0 GA.
# Checkpoints enable session recovery and state persistence.
# ─────────────────────────────────────────────────────────────────────────────

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class CheckpointData:
    """
    Represents checkpoint data for an orchestration session.
    
    Checkpoints capture the complete state of an orchestration, allowing
    it to be resumed after interruptions (crashes, disconnects, etc.).
    
    Attributes:
        session_id: Unique identifier for the orchestration session
        orchestration_type: Type of orchestration (magentic, sequential, etc.)
        current_step: Current step in the orchestration
        total_steps: Total expected steps (if known)
        agent_states: State for each agent in the orchestration
        plan: Current execution plan (for Magentic orchestration)
        messages: Conversation history
        metadata: Additional orchestration metadata
        created_at: When the checkpoint was created
        updated_at: When the checkpoint was last updated
    """
    session_id: str
    orchestration_type: str = "magentic"
    current_step: int = 0
    total_steps: Optional[int] = None
    agent_states: dict[str, Any] = field(default_factory=dict)
    plan: Optional[dict[str, Any]] = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "orchestration_type": self.orchestration_type,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "agent_states": self.agent_states,
            "plan": self.plan,
            "messages": self.messages,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointData":
        """Create checkpoint from dictionary."""
        return cls(
            session_id=data["session_id"],
            orchestration_type=data.get("orchestration_type", "magentic"),
            current_step=data.get("current_step", 0),
            total_steps=data.get("total_steps"),
            agent_states=data.get("agent_states", {}),
            plan=data.get("plan"),
            messages=data.get("messages", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
        )
    
    def to_json(self) -> str:
        """Convert checkpoint to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "CheckpointData":
        """Create checkpoint from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def update_step(self, step: int, agent_name: Optional[str] = None, agent_state: Optional[dict] = None) -> None:
        """
        Update checkpoint with new step information.
        
        Args:
            step: New current step
            agent_name: Name of agent that completed (optional)
            agent_state: State of the agent (optional)
        """
        self.current_step = step
        self.updated_at = datetime.now(timezone.utc)
        
        if agent_name and agent_state:
            self.agent_states[agent_name] = agent_state
    
    def add_message(self, role: str, content: str, agent_name: Optional[str] = None) -> None:
        """
        Add a message to the checkpoint.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            agent_name: Name of agent that sent the message (optional)
        """
        self.messages.append({
            "role": role,
            "content": content,
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.updated_at = datetime.now(timezone.utc)


class CheckpointStore(ABC):
    """
    Abstract base class for checkpoint stores.
    
    Checkpoint stores persist orchestration state to enable recovery
    after interruptions. Implementations can use any backend.
    
    MAF 1.0 GA Pattern:
        Checkpoint stores are attached to orchestrations to automatically
        save and restore state.
    
    Usage:
        store = FileCheckpointStore("./checkpoints")
        
        # Save checkpoint
        await store.save(checkpoint_data)
        
        # Load checkpoint
        checkpoint = await store.load("session-123")
        
        # Resume orchestration from checkpoint
        orchestration.resume_from(checkpoint)
    """
    
    @abstractmethod
    async def save(self, checkpoint: CheckpointData) -> None:
        """
        Save a checkpoint.
        
        Args:
            checkpoint: Checkpoint data to save
        """
        pass
    
    @abstractmethod
    async def load(self, session_id: str) -> Optional[CheckpointData]:
        """
        Load a checkpoint by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            CheckpointData if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """
        List all session IDs with checkpoints.
        
        Args:
            pattern: Glob pattern for filtering
            
        Returns:
            List of session IDs
        """
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """
        Check if a checkpoint exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if checkpoint exists
        """
        pass
    
    async def save_if_newer(self, checkpoint: CheckpointData) -> bool:
        """
        Save checkpoint only if it's newer than the existing one.
        
        Args:
            checkpoint: Checkpoint data to save
            
        Returns:
            True if saved, False if existing is newer
        """
        existing = await self.load(checkpoint.session_id)
        
        if existing and existing.updated_at >= checkpoint.updated_at:
            return False
        
        await self.save(checkpoint)
        return True
