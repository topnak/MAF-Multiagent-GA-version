# ─────────────────────────────────────────────────────────────────────────────
# Base Skill
# ─────────────────────────────────────────────────────────────────────────────
# Abstract base class for programmatic skills.
# Allows skills to be implemented in code rather than just markdown.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from skills.skill_loader import Skill, SkillMetadata

# Configure module logger
logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """
    Abstract base class for programmatic skills.
    
    While most skills are defined as SKILL.md files with markdown content,
    some skills benefit from programmatic implementation. This base class
    provides a structure for code-based skills.
    
    Usage:
        class CalculationSkill(BaseSkill):
            @property
            def name(self) -> str:
                return "calculation"
            
            @property
            def description(self) -> str:
                return "Performs mathematical calculations"
            
            async def execute(self, task: str, context: dict) -> str:
                # Implement skill logic
                return "Result: 42"
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the skill name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the skill description."""
        pass
    
    @property
    def tags(self) -> list[str]:
        """Get skill tags for discovery."""
        return []
    
    @property
    def version(self) -> str:
        """Get skill version."""
        return "1.0.0"
    
    @property
    def requires(self) -> list[str]:
        """Get required dependencies."""
        return []
    
    @property
    def tools(self) -> list[str]:
        """Get tools this skill may use."""
        return []
    
    @abstractmethod
    async def execute(self, task: str, context: Optional[dict] = None) -> str:
        """
        Execute the skill.
        
        Args:
            task: The task description
            context: Optional context
            
        Returns:
            Skill execution result
        """
        pass
    
    def get_prompt_content(self) -> str:
        """
        Get content to inject into prompts.
        
        Override this to provide instructions for LLM-based agents.
        
        Returns:
            Prompt content string
        """
        return f"Use the {self.name} skill for: {self.description}"
    
    def to_skill(self) -> Skill:
        """
        Convert to a Skill object for registry compatibility.
        
        Returns:
            Skill object
        """
        from pathlib import Path
        
        metadata = SkillMetadata(
            name=self.name,
            description=self.description,
            tags=self.tags,
            version=self.version,
            requires=self.requires,
            tools=self.tools,
        )
        
        return Skill(
            metadata=metadata,
            content=self.get_prompt_content(),
            source_path=Path(f"<programmatic:{self.name}>"),
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


# ─────────────────────────────────────────────────────────────────────────────
# Example Skills
# ─────────────────────────────────────────────────────────────────────────────

class DataAnalysisSkill(BaseSkill):
    """
    Example skill for data analysis tasks.
    """
    
    @property
    def name(self) -> str:
        return "data-analysis"
    
    @property
    def description(self) -> str:
        return "Analyzes data patterns and generates insights"
    
    @property
    def tags(self) -> list[str]:
        return ["analytics", "data", "insights"]
    
    @property
    def tools(self) -> list[str]:
        return ["snowflake_mcp"]
    
    async def execute(self, task: str, context: Optional[dict] = None) -> str:
        """Execute data analysis."""
        # In a real implementation, this would perform actual analysis
        return f"Data analysis complete for: {task}"
    
    def get_prompt_content(self) -> str:
        return """
# Data Analysis Skill

You are skilled in data analysis. When analyzing data:

1. **Understand the data**: Identify data types, distributions, and quality issues
2. **Look for patterns**: Find trends, correlations, and anomalies
3. **Generate insights**: Transform findings into actionable recommendations
4. **Visualize appropriately**: Suggest charts/graphs that best represent the data

Key metrics to consider:
- Trends over time
- Comparisons across segments
- Statistical significance
- Outliers and anomalies
"""


class RetailDomainSkill(BaseSkill):
    """
    Example skill for retail domain knowledge.
    """
    
    @property
    def name(self) -> str:
        return "retail-domain"
    
    @property
    def description(self) -> str:
        return "Provides retail industry knowledge and best practices"
    
    @property
    def tags(self) -> list[str]:
        return ["retail", "domain", "commerce"]
    
    async def execute(self, task: str, context: Optional[dict] = None) -> str:
        """Provide retail expertise."""
        return f"Retail analysis for: {task}"
    
    def get_prompt_content(self) -> str:
        return """
# Retail Domain Skill

You have expertise in retail operations. Apply these concepts:

## Key Metrics
- **Sell-through rate**: Units sold / Units received
- **GMROI**: Gross margin / Average inventory cost
- **Inventory turnover**: COGS / Average inventory
- **Basket size**: Revenue / Number of transactions

## Seasonal Patterns
- Plan for seasonal peaks (Q4 holidays, back-to-school, etc.)
- Adjust inventory levels 6-8 weeks before peak seasons
- Consider weather impacts on category performance

## Best Practices
- Maintain 95%+ in-stock rate on A items
- Review slow movers quarterly
- Optimize planogram space by sales velocity
"""
