# ─────────────────────────────────────────────────────────────────────────────
# Skill Registry
# ─────────────────────────────────────────────────────────────────────────────
# Central registry for managing skills and providing discovery.
# Handles skill lifecycle, dependency resolution, and agent assignment.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Any, Optional

from skills.skill_loader import Skill, SkillLoader, SkillMetadata

# Configure module logger
logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Central registry for skill management.
    
    The registry:
    1. Maintains a catalog of available skills
    2. Provides skill discovery by tags/capabilities
    3. Manages skill assignments to agents
    4. Handles skill dependencies
    
    Usage:
        registry = SkillRegistry(skills_dir="./skills")
        
        # List available skills
        skills = registry.list_skills()
        
        # Find skills by tag
        retail_skills = registry.find_by_tag("retail")
        
        # Get skill for an agent
        skill = registry.get_skill_for_agent("MerchPlanner")
    """
    
    def __init__(
        self,
        skills_dir: Optional[str] = None,
        skills_dirs: Optional[list[str]] = None,
        auto_load: bool = True,
    ):
        """
        Initialize the skill registry.
        
        Args:
            skills_dir: Directory containing skills
            skills_dirs: Multiple skill directories
            auto_load: Whether to load skills on initialization
        """
        self._loader = SkillLoader(
            skills_dir=skills_dir,
            skills_dirs=skills_dirs,
        )
        
        # Skill catalog
        self._skills: dict[str, Skill] = {}
        
        # Agent-to-skill mapping
        self._agent_skills: dict[str, list[str]] = {}
        
        # Tag index for discovery
        self._tag_index: dict[str, list[str]] = {}
        
        if auto_load:
            self.refresh()
        
        logger.info("SkillRegistry initialized")
    
    def refresh(self) -> int:
        """
        Refresh the skill catalog from disk.
        
        Returns:
            Number of skills loaded
        """
        self._skills.clear()
        self._tag_index.clear()
        
        skills = self._loader.load_all()
        
        for skill in skills:
            self._skills[skill.name] = skill
            
            # Build tag index
            for tag in skill.metadata.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(skill.name)
        
        logger.info(f"Refreshed registry with {len(self._skills)} skills")
        return len(self._skills)
    
    def get(self, skill_name: str) -> Optional[Skill]:
        """
        Get a skill by name.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill or None if not found
        """
        return self._skills.get(skill_name)
    
    def list_skills(self) -> list[dict[str, Any]]:
        """
        List all available skills.
        
        Returns:
            List of skill information dictionaries
        """
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "tags": skill.metadata.tags,
                "version": skill.metadata.version,
            }
            for skill in self._skills.values()
        ]
    
    def find_by_tag(self, tag: str) -> list[Skill]:
        """
        Find skills by tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching skills
        """
        skill_names = self._tag_index.get(tag, [])
        return [self._skills[name] for name in skill_names if name in self._skills]
    
    def find_by_tags(self, tags: list[str], require_all: bool = False) -> list[Skill]:
        """
        Find skills by multiple tags.
        
        Args:
            tags: Tags to search for
            require_all: If True, skill must have ALL tags
            
        Returns:
            List of matching skills
        """
        if require_all:
            # Skill must have all tags
            matching = []
            for skill in self._skills.values():
                if all(tag in skill.metadata.tags for tag in tags):
                    matching.append(skill)
            return matching
        else:
            # Skill must have at least one tag
            matching_names: set[str] = set()
            for tag in tags:
                matching_names.update(self._tag_index.get(tag, []))
            return [self._skills[name] for name in matching_names if name in self._skills]
    
    def assign_to_agent(self, agent_name: str, skill_names: list[str]) -> None:
        """
        Assign skills to an agent.
        
        Args:
            agent_name: Name of the agent
            skill_names: List of skill names to assign
        """
        self._agent_skills[agent_name] = skill_names
        logger.info(f"Assigned {len(skill_names)} skills to {agent_name}")
    
    def get_agent_skills(self, agent_name: str) -> list[Skill]:
        """
        Get skills assigned to an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of assigned skills
        """
        skill_names = self._agent_skills.get(agent_name, [])
        return [self._skills[name] for name in skill_names if name in self._skills]
    
    def get_agent_prompt_additions(self, agent_name: str) -> str:
        """
        Get skill content formatted for agent prompt injection.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Combined skill content for prompts
        """
        skills = self.get_agent_skills(agent_name)
        
        if not skills:
            return ""
        
        return "\n".join(skill.get_prompt_injection() for skill in skills)
    
    def resolve_dependencies(self, skill_name: str) -> list[str]:
        """
        Resolve skill dependencies.
        
        Returns list of skill names in dependency order.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            List of skill names including dependencies
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return []
        
        resolved: list[str] = []
        seen: set[str] = set()
        
        def _resolve(name: str) -> None:
            if name in seen:
                return
            seen.add(name)
            
            s = self._skills.get(name)
            if not s:
                return
            
            for dep in s.metadata.requires:
                _resolve(dep)
            
            resolved.append(name)
        
        _resolve(skill_name)
        return resolved
    
    def get_all_tags(self) -> list[str]:
        """Get all available tags."""
        return list(self._tag_index.keys())
    
    def register_skill(self, skill: Skill) -> None:
        """
        Register a skill directly (without loading from file).
        
        Args:
            skill: Skill to register
        """
        self._skills[skill.name] = skill
        
        for tag in skill.metadata.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if skill.name not in self._tag_index[tag]:
                self._tag_index[tag].append(skill.name)
        
        logger.info(f"Registered skill: {skill.name}")
    
    def unregister_skill(self, skill_name: str) -> bool:
        """
        Unregister a skill.
        
        Args:
            skill_name: Name of skill to remove
            
        Returns:
            True if skill was removed
        """
        if skill_name not in self._skills:
            return False
        
        skill = self._skills.pop(skill_name)
        
        # Remove from tag index
        for tag in skill.metadata.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [n for n in self._tag_index[tag] if n != skill_name]
        
        logger.info(f"Unregistered skill: {skill_name}")
        return True
