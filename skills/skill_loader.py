# ─────────────────────────────────────────────────────────────────────────────
# Skill Loader
# ─────────────────────────────────────────────────────────────────────────────
# Loads skills from SKILL.md files with YAML frontmatter.
# Skills provide domain-specific knowledge and capabilities.
#
# SKILL.md Format:
# ---
# name: skill-name
# description: What the skill does
# tags: [tag1, tag2]
# version: 1.0.0
# ---
# 
# # Skill Content
# Markdown content with instructions, examples, etc.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import yaml

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """
    Metadata extracted from SKILL.md frontmatter.
    
    Attributes:
        name: Unique skill identifier
        description: Human-readable description
        tags: Categorization tags
        version: Skill version
        author: Skill author
        requires: Dependencies on other skills
        tools: Tools this skill may use
    """
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: Optional[str] = None
    requires: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "requires": self.requires,
            "tools": self.tools,
        }


@dataclass
class Skill:
    """
    A loaded skill with metadata and content.
    
    Attributes:
        metadata: Parsed YAML frontmatter
        content: Markdown content (instructions)
        source_path: Path to the SKILL.md file
        loaded_at: When the skill was loaded
    """
    metadata: SkillMetadata
    content: str
    source_path: Path
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def name(self) -> str:
        """Get skill name."""
        return self.metadata.name
    
    @property
    def description(self) -> str:
        """Get skill description."""
        return self.metadata.description
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "source_path": str(self.source_path),
            "loaded_at": self.loaded_at.isoformat(),
        }
    
    def get_prompt_injection(self) -> str:
        """
        Get the skill content formatted for prompt injection.
        
        Returns:
            Formatted skill content ready for inclusion in prompts
        """
        return f"""
<skill name="{self.name}">
{self.content}
</skill>
"""


class SkillLoader:
    """
    Loads skills from SKILL.md files.
    
    The loader:
    1. Scans directories for SKILL.md files
    2. Parses YAML frontmatter for metadata
    3. Extracts markdown content for instructions
    4. Validates and caches loaded skills
    
    Usage:
        loader = SkillLoader(skills_dir="./skills")
        
        # Load a specific skill
        skill = loader.load("retail-analysis")
        
        # Load all skills
        skills = loader.load_all()
        
        # Get skill content for prompt
        prompt_addition = skill.get_prompt_injection()
    """
    
    # Regex for YAML frontmatter
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )
    
    def __init__(
        self,
        skills_dir: Optional[str] = None,
        skills_dirs: Optional[list[str]] = None,
    ):
        """
        Initialize the skill loader.
        
        Args:
            skills_dir: Single directory containing SKILL.md files
            skills_dirs: Multiple directories to search
        """
        self._dirs: list[Path] = []
        
        if skills_dir:
            self._dirs.append(Path(skills_dir))
        
        if skills_dirs:
            self._dirs.extend(Path(d) for d in skills_dirs)
        
        if not self._dirs:
            # Default to 'skills' directory in current working dir
            self._dirs.append(Path.cwd() / "skills")
        
        # Cache loaded skills
        self._cache: dict[str, Skill] = {}
        
        logger.info(f"SkillLoader initialized with {len(self._dirs)} directories")
    
    def load(self, skill_name: str) -> Optional[Skill]:
        """
        Load a skill by name.
        
        Searches configured directories for a SKILL.md file in a folder
        matching the skill name, or a file named {skill_name}.skill.md
        
        Args:
            skill_name: Name of the skill to load
            
        Returns:
            Loaded Skill or None if not found
        """
        # Check cache first
        if skill_name in self._cache:
            logger.debug(f"Returning cached skill: {skill_name}")
            return self._cache[skill_name]
        
        # Search directories
        for dir_path in self._dirs:
            # Option 1: skills/{skill_name}/SKILL.md
            skill_path = dir_path / skill_name / "SKILL.md"
            if skill_path.exists():
                return self._load_from_path(skill_path)
            
            # Option 2: skills/{skill_name}.skill.md
            skill_path = dir_path / f"{skill_name}.skill.md"
            if skill_path.exists():
                return self._load_from_path(skill_path)
            
            # Option 3: {skill_name}/SKILL.md
            skill_path = dir_path / skill_name / "SKILL.md"
            if skill_path.exists():
                return self._load_from_path(skill_path)
        
        logger.warning(f"Skill not found: {skill_name}")
        return None
    
    def load_all(self) -> list[Skill]:
        """
        Load all skills from configured directories.
        
        Returns:
            List of all loaded skills
        """
        skills: list[Skill] = []
        
        for dir_path in self._dirs:
            if not dir_path.exists():
                continue
            
            # Find all SKILL.md files
            for skill_file in dir_path.rglob("SKILL.md"):
                skill = self._load_from_path(skill_file)
                if skill:
                    skills.append(skill)
            
            # Find all *.skill.md files
            for skill_file in dir_path.rglob("*.skill.md"):
                skill = self._load_from_path(skill_file)
                if skill:
                    skills.append(skill)
        
        logger.info(f"Loaded {len(skills)} skills")
        return skills
    
    def _load_from_path(self, path: Path) -> Optional[Skill]:
        """Load a skill from a file path."""
        try:
            content = path.read_text(encoding="utf-8")
            
            # Parse frontmatter
            metadata, body = self._parse_frontmatter(content)
            
            if not metadata:
                # Use filename as skill name
                name = path.stem.replace(".skill", "") if ".skill" in path.stem else path.parent.name
                metadata = SkillMetadata(name=name)
            
            skill = Skill(
                metadata=metadata,
                content=body.strip(),
                source_path=path,
            )
            
            # Cache the skill
            self._cache[skill.name] = skill
            
            logger.info(f"Loaded skill: {skill.name} from {path}")
            return skill
            
        except Exception as e:
            logger.error(f"Failed to load skill from {path}: {e}")
            return None
    
    def _parse_frontmatter(self, content: str) -> tuple[Optional[SkillMetadata], str]:
        """
        Parse YAML frontmatter from content.
        
        Args:
            content: Raw file content
            
        Returns:
            Tuple of (metadata, body content)
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        
        if not match:
            return None, content
        
        frontmatter_yaml = match.group(1)
        body = content[match.end():]
        
        try:
            data = yaml.safe_load(frontmatter_yaml)
            
            if not isinstance(data, dict):
                return None, content
            
            metadata = SkillMetadata(
                name=data.get("name", "unnamed"),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                version=data.get("version", "1.0.0"),
                author=data.get("author"),
                requires=data.get("requires", []),
                tools=data.get("tools", []),
            )
            
            return metadata, body
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML frontmatter: {e}")
            return None, content
    
    def reload(self, skill_name: str) -> Optional[Skill]:
        """
        Reload a skill, bypassing cache.
        
        Args:
            skill_name: Name of skill to reload
            
        Returns:
            Reloaded Skill or None
        """
        # Remove from cache
        self._cache.pop(skill_name, None)
        
        # Load fresh
        return self.load(skill_name)
    
    def clear_cache(self) -> None:
        """Clear the skill cache."""
        self._cache.clear()
        logger.info("Skill cache cleared")
    
    def get_cached_skills(self) -> dict[str, Skill]:
        """Get all cached skills."""
        return dict(self._cache)
