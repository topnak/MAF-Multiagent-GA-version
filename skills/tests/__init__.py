# ─────────────────────────────────────────────────────────────────────────────
# Skills Module Tests
# ─────────────────────────────────────────────────────────────────────────────
# Unit tests for skill loader, registry, and base skill.
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from pathlib import Path
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from skills.skill_loader import SkillLoader, Skill, SkillMetadata
from skills.skill_registry import SkillRegistry
from skills.base_skill import BaseSkill, DataAnalysisSkill, RetailDomainSkill


# ─────────────────────────────────────────────────────────────────────────────
# SkillMetadata Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""
    
    def test_create_metadata(self):
        """Test creating skill metadata."""
        metadata = SkillMetadata(
            name="test-skill",
            description="A test skill",
            tags=["test", "example"],
        )
        
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert len(metadata.tags) == 2
        assert metadata.version == "1.0.0"  # default
    
    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            tags=["tag1"],
            author="Test Author",
        )
        
        data = metadata.to_dict()
        
        assert data["name"] == "test-skill"
        assert data["author"] == "Test Author"


# ─────────────────────────────────────────────────────────────────────────────
# Skill Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSkill:
    """Tests for Skill dataclass."""
    
    def test_create_skill(self):
        """Test creating a skill."""
        metadata = SkillMetadata(name="test", description="Test skill")
        skill = Skill(
            metadata=metadata,
            content="# Test Content\nSome instructions.",
            source_path=Path("/test/SKILL.md"),
        )
        
        assert skill.name == "test"
        assert skill.description == "Test skill"
        assert "Test Content" in skill.content
    
    def test_get_prompt_injection(self):
        """Test getting prompt injection content."""
        metadata = SkillMetadata(name="test", description="Test")
        skill = Skill(
            metadata=metadata,
            content="Instructions here",
            source_path=Path("/test/SKILL.md"),
        )
        
        injection = skill.get_prompt_injection()
        
        assert '<skill name="test">' in injection
        assert "Instructions here" in injection
        assert "</skill>" in injection


# ─────────────────────────────────────────────────────────────────────────────
# SkillLoader Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillLoader:
    """Tests for SkillLoader."""
    
    def test_init_default(self):
        """Test loader initialization with defaults."""
        loader = SkillLoader()
        
        assert len(loader._dirs) == 1
    
    def test_init_custom_dir(self):
        """Test loader with custom directory."""
        loader = SkillLoader(skills_dir="./custom_skills")
        
        assert Path("./custom_skills") in [Path(d) for d in loader._dirs]
    
    def test_parse_frontmatter(self):
        """Test parsing YAML frontmatter."""
        loader = SkillLoader()
        
        content = """---
name: test-skill
description: A test skill
tags: [testing, example]
version: 2.0.0
---

# Skill Content

This is the skill body.
"""
        
        metadata, body = loader._parse_frontmatter(content)
        
        assert metadata is not None
        assert metadata.name == "test-skill"
        assert metadata.description == "A test skill"
        assert "testing" in metadata.tags
        assert metadata.version == "2.0.0"
        assert "Skill Content" in body
    
    def test_parse_frontmatter_no_yaml(self):
        """Test parsing content without frontmatter."""
        loader = SkillLoader()
        
        content = "# Just Markdown\nNo frontmatter here."
        
        metadata, body = loader._parse_frontmatter(content)
        
        assert metadata is None
        assert body == content
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        loader = SkillLoader()
        loader._cache["test"] = Skill(
            metadata=SkillMetadata(name="test"),
            content="",
            source_path=Path("/test"),
        )
        
        loader.clear_cache()
        
        assert len(loader._cache) == 0


# ─────────────────────────────────────────────────────────────────────────────
# SkillRegistry Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSkillRegistry:
    """Tests for SkillRegistry."""
    
    def test_init(self):
        """Test registry initialization."""
        registry = SkillRegistry(skills_dir="./nonexistent", auto_load=False)
        
        assert len(registry._skills) == 0
    
    def test_register_skill(self):
        """Test registering a skill manually."""
        registry = SkillRegistry(auto_load=False)
        
        metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            tags=["test"],
        )
        skill = Skill(
            metadata=metadata,
            content="Content",
            source_path=Path("/test"),
        )
        
        registry.register_skill(skill)
        
        assert "test-skill" in registry._skills
        assert "test" in registry._tag_index
    
    def test_unregister_skill(self):
        """Test unregistering a skill."""
        registry = SkillRegistry(auto_load=False)
        
        metadata = SkillMetadata(name="to-remove", tags=["temp"])
        skill = Skill(metadata=metadata, content="", source_path=Path("/test"))
        registry.register_skill(skill)
        
        result = registry.unregister_skill("to-remove")
        
        assert result is True
        assert "to-remove" not in registry._skills
    
    def test_find_by_tag(self):
        """Test finding skills by tag."""
        registry = SkillRegistry(auto_load=False)
        
        # Register skills
        for name, tags in [("s1", ["a", "b"]), ("s2", ["b", "c"]), ("s3", ["c"])]:
            metadata = SkillMetadata(name=name, tags=tags)
            skill = Skill(metadata=metadata, content="", source_path=Path(f"/{name}"))
            registry.register_skill(skill)
        
        # Find by tag
        results = registry.find_by_tag("b")
        
        assert len(results) == 2
        assert all(s.name in ["s1", "s2"] for s in results)
    
    def test_assign_to_agent(self):
        """Test assigning skills to an agent."""
        registry = SkillRegistry(auto_load=False)
        
        metadata = SkillMetadata(name="agent-skill")
        skill = Skill(metadata=metadata, content="Content", source_path=Path("/test"))
        registry.register_skill(skill)
        
        registry.assign_to_agent("TestAgent", ["agent-skill"])
        
        skills = registry.get_agent_skills("TestAgent")
        assert len(skills) == 1
        assert skills[0].name == "agent-skill"
    
    def test_get_agent_prompt_additions(self):
        """Test getting prompt additions for an agent."""
        registry = SkillRegistry(auto_load=False)
        
        metadata = SkillMetadata(name="prompt-skill")
        skill = Skill(metadata=metadata, content="Skill instructions", source_path=Path("/test"))
        registry.register_skill(skill)
        registry.assign_to_agent("TestAgent", ["prompt-skill"])
        
        additions = registry.get_agent_prompt_additions("TestAgent")
        
        assert "prompt-skill" in additions
        assert "Skill instructions" in additions


# ─────────────────────────────────────────────────────────────────────────────
# BaseSkill Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBaseSkill:
    """Tests for BaseSkill and example implementations."""
    
    def test_data_analysis_skill(self):
        """Test DataAnalysisSkill."""
        skill = DataAnalysisSkill()
        
        assert skill.name == "data-analysis"
        assert "analytics" in skill.tags
        assert "snowflake_mcp" in skill.tools
    
    @pytest.mark.asyncio
    async def test_data_analysis_execute(self):
        """Test executing DataAnalysisSkill."""
        skill = DataAnalysisSkill()
        
        result = await skill.execute("Analyze sales trends")
        
        assert "Data analysis complete" in result
    
    def test_retail_domain_skill(self):
        """Test RetailDomainSkill."""
        skill = RetailDomainSkill()
        
        assert skill.name == "retail-domain"
        assert "retail" in skill.tags
    
    def test_to_skill_conversion(self):
        """Test converting BaseSkill to Skill."""
        base_skill = DataAnalysisSkill()
        skill = base_skill.to_skill()
        
        assert skill.name == "data-analysis"
        assert skill.metadata.description == base_skill.description
    
    def test_get_prompt_content(self):
        """Test getting prompt content."""
        skill = RetailDomainSkill()
        
        content = skill.get_prompt_content()
        
        assert "Retail Domain Skill" in content
        assert "GMROI" in content
