# ─────────────────────────────────────────────────────────────────────────────
# Content Safety Middleware
# ─────────────────────────────────────────────────────────────────────────────
# Provides content filtering and safety guardrails for agent interactions.
# Filters harmful content, PII, and enforces content policies.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from .base_middleware import (
    MiddlewareBase,
    MiddlewareContext,
    MiddlewareResponse,
    NextHandler,
    NextResponseHandler,
)

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class ContentSafetyConfig:
    """
    Configuration for content safety middleware.
    
    Attributes:
        blocked_keywords: List of keywords to block in input/output
        pii_patterns: Regex patterns for PII detection
        redact_pii: Whether to redact PII instead of blocking
        max_input_length: Maximum allowed input length
        max_output_length: Maximum allowed output length
        block_code_execution: Block potential code execution attempts
        enabled: Whether content safety is enabled
    """
    # Keywords that trigger blocking (case-insensitive)
    blocked_keywords: list[str] = field(default_factory=lambda: [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard your instructions",
        "forget your rules",
        "bypass safety",
        "jailbreak",
    ])
    
    # Regex patterns for PII detection
    pii_patterns: dict[str, str] = field(default_factory=lambda: {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_au": r'\b(?:\+?61|0)[2-478](?:[ -]?\d){8}\b',
        "phone_us": r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        "ssn_us": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        "tfn_au": r'\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b',  # Australian Tax File Number
        "medicare_au": r'\b\d{10,11}\b',
    })
    
    # Whether to redact PII instead of blocking
    redact_pii: bool = True
    
    # PII redaction placeholder
    redaction_placeholder: str = "[REDACTED]"
    
    # Maximum message lengths
    max_input_length: int = 10000
    max_output_length: int = 50000
    
    # Block potential prompt injection patterns
    block_code_execution: bool = True
    
    # Patterns that might indicate code execution attempts
    code_execution_patterns: list[str] = field(default_factory=lambda: [
        r'```python[\s\S]*exec\s*\(',
        r'```python[\s\S]*eval\s*\(',
        r'__import__\s*\(',
        r'subprocess\.',
        r'os\.system\s*\(',
    ])
    
    # Whether content safety is enabled
    enabled: bool = True
    
    @classmethod
    def strict(cls) -> "ContentSafetyConfig":
        """
        Create strict content safety configuration.
        
        Returns:
            ContentSafetyConfig: Strict configuration for production
        """
        return cls(
            redact_pii=False,  # Block instead of redact
            max_input_length=5000,
            max_output_length=20000,
            block_code_execution=True,
            enabled=True,
        )
    
    @classmethod
    def permissive(cls) -> "ContentSafetyConfig":
        """
        Create permissive content safety configuration for development.
        
        Returns:
            ContentSafetyConfig: Permissive configuration for development
        """
        return cls(
            blocked_keywords=[],
            redact_pii=True,
            max_input_length=50000,
            max_output_length=100000,
            block_code_execution=False,
            enabled=True,
        )


class ContentSafetyMiddleware(MiddlewareBase):
    """
    Content safety middleware for MAF agents.
    
    This middleware provides guardrails for agent interactions:
    - Blocks harmful or malicious content
    - Detects and optionally redacts PII
    - Enforces content length limits
    - Blocks potential prompt injection attacks
    
    Features:
    - Configurable keyword blocking
    - PII detection with regex patterns
    - Content length enforcement
    - Prompt injection detection
    
    Usage:
        config = ContentSafetyConfig()
        safety = ContentSafetyMiddleware(config)
        
        # In pipeline
        pipeline = MiddlewarePipeline([safety])
        response = await pipeline.execute(context, agent_handler)
    """
    
    def __init__(self, config: Optional[ContentSafetyConfig] = None):
        """
        Initialize content safety middleware.
        
        Args:
            config: Content safety configuration. If None, uses default config.
        """
        self.config = config or ContentSafetyConfig()
        
        # Compile regex patterns for efficiency
        self._pii_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.config.pii_patterns.items()
        }
        
        self._code_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.config.code_execution_patterns
        ]
    
    async def on_request(
        self,
        context: MiddlewareContext,
        next_handler: NextHandler,
    ) -> MiddlewareResponse:
        """
        Check and filter incoming request content.
        
        Args:
            context: Request context with messages
            next_handler: Next middleware/agent in chain
            
        Returns:
            MiddlewareResponse: Response or blocked message
        """
        if not self.config.enabled:
            return await next_handler(context)
        
        # Get the last user message
        last_message = context.get_last_message()
        if not last_message:
            return await next_handler(context)
        
        content = last_message.get("content", "")
        
        # Check content length
        if len(content) > self.config.max_input_length:
            logger.warning(
                f"Input too long ({len(content)} chars), max {self.config.max_input_length}"
            )
            return MiddlewareResponse(
                content=f"Input too long. Maximum length is {self.config.max_input_length} characters.",
                blocked=True,
                block_reason="input_too_long",
            )
        
        # Check for blocked keywords (potential prompt injection)
        blocked_keyword = self._check_blocked_keywords(content)
        if blocked_keyword:
            logger.warning(
                f"Blocked keyword detected in input: '{blocked_keyword}'"
            )
            return MiddlewareResponse(
                content="Your message contains content that cannot be processed. Please rephrase.",
                blocked=True,
                block_reason="blocked_keyword",
            )
        
        # Check for code execution attempts
        if self.config.block_code_execution:
            code_pattern = self._check_code_execution(content)
            if code_pattern:
                logger.warning(
                    f"Potential code execution attempt detected, request_id={context.request_id}"
                )
                return MiddlewareResponse(
                    content="Your message contains content that appears to be a code execution attempt.",
                    blocked=True,
                    block_reason="code_execution_attempt",
                )
        
        # Handle PII in input
        pii_findings = self._detect_pii(content)
        if pii_findings:
            logger.info(f"PII detected in input: {list(pii_findings.keys())}")
            
            if self.config.redact_pii:
                # Redact PII and continue
                redacted_content = self._redact_pii(content, pii_findings)
                last_message["content"] = redacted_content
                context.set_metadata("pii_redacted_input", True)
                context.set_metadata("pii_types_found", list(pii_findings.keys()))
            else:
                # Block request with PII
                return MiddlewareResponse(
                    content=(
                        "Your message contains sensitive information (PII) that cannot be "
                        "processed. Please remove personal data and try again."
                    ),
                    blocked=True,
                    block_reason="pii_detected",
                    metadata={"pii_types": list(pii_findings.keys())},
                )
        
        # Continue to next handler
        return await next_handler(context)
    
    async def on_response(
        self,
        context: MiddlewareContext,
        response: MiddlewareResponse,
        next_handler: NextResponseHandler,
    ) -> MiddlewareResponse:
        """
        Check and filter outgoing response content.
        
        Args:
            context: Original request context
            response: Response from agent
            next_handler: Next middleware in chain
            
        Returns:
            MiddlewareResponse: Filtered response
        """
        if not self.config.enabled or response.blocked:
            return await next_handler(context, response)
        
        content = response.content
        
        # Check output length
        if len(content) > self.config.max_output_length:
            logger.warning(
                f"Output too long ({len(content)} chars), truncating"
            )
            content = content[:self.config.max_output_length]
            content += "\n\n[Response truncated due to length limits]"
            response.content = content
        
        # Check for PII in output (agents shouldn't leak PII)
        pii_findings = self._detect_pii(content)
        if pii_findings:
            logger.warning(f"PII detected in agent output: {list(pii_findings.keys())}")
            
            # Always redact PII in output (don't block, just clean)
            response.content = self._redact_pii(content, pii_findings)
            response.metadata["pii_redacted_output"] = True
            response.metadata["pii_types_found"] = list(pii_findings.keys())
        
        return await next_handler(context, response)
    
    def _check_blocked_keywords(self, content: str) -> Optional[str]:
        """
        Check content for blocked keywords.
        
        Args:
            content: Content to check
            
        Returns:
            str: First blocked keyword found, or None
        """
        content_lower = content.lower()
        for keyword in self.config.blocked_keywords:
            if keyword.lower() in content_lower:
                return keyword
        return None
    
    def _check_code_execution(self, content: str) -> Optional[str]:
        """
        Check content for code execution attempts.
        
        Args:
            content: Content to check
            
        Returns:
            str: Pattern that matched, or None
        """
        for pattern in self._code_patterns:
            if pattern.search(content):
                return pattern.pattern
        return None
    
    def _detect_pii(self, content: str) -> dict[str, list[str]]:
        """
        Detect PII patterns in content.
        
        Args:
            content: Content to scan
            
        Returns:
            dict: Mapping of PII type to list of matches
        """
        findings = {}
        for pii_type, pattern in self._pii_patterns.items():
            matches = pattern.findall(content)
            if matches:
                findings[pii_type] = matches
        return findings
    
    def _redact_pii(self, content: str, pii_findings: dict[str, list[str]]) -> str:
        """
        Redact PII from content.
        
        Args:
            content: Content with PII
            pii_findings: PII matches to redact
            
        Returns:
            str: Content with PII redacted
        """
        redacted = content
        for pii_type, matches in pii_findings.items():
            for match in matches:
                redacted = redacted.replace(match, self.config.redaction_placeholder)
        return redacted
    
    def add_blocked_keyword(self, keyword: str) -> None:
        """
        Add a keyword to the blocked list.
        
        Args:
            keyword: Keyword to block
        """
        if keyword not in self.config.blocked_keywords:
            self.config.blocked_keywords.append(keyword)
    
    def add_pii_pattern(self, name: str, pattern: str) -> None:
        """
        Add a PII detection pattern.
        
        Args:
            name: Name of the PII type
            pattern: Regex pattern for detection
        """
        self.config.pii_patterns[name] = pattern
        self._pii_patterns[name] = re.compile(pattern, re.IGNORECASE)
