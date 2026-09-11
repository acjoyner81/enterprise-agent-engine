"""Prompt Injection and Jailbreak Guardrail Detector."""

import re
from typing import ClassVar

from pydantic import BaseModel, Field


class InjectionCheckResult(BaseModel):
    """Result of prompt injection and security pattern analysis."""

    is_safe: bool = True
    threat_level: str = "SAFE"  # SAFE, LOW, HIGH, CRITICAL
    detected_patterns: list[str] = Field(default_factory=list)
    reason: str = "Prompt evaluated as safe."


class InjectionDetector:
    """Detects adversarial injection attacks, jailbreak attempts, and system prompt leakage."""

    # inside InjectionDetector class:
    CRITICAL_PATTERNS: ClassVar[list[tuple[str, re.Pattern]]] = [
        (
            "INSTRUCTION_OVERRIDE",
            re.compile(
                r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|commands)",
                re.IGNORECASE,
            ),
        ),
        (
            "SYSTEM_PROMPT_EXTRACTION",
            re.compile(
                r"(?:repeat|print|reveal|show|output)\s+(?:your\s+)?(?:system\s+prompt|initial\s+instructions|system\s+message)",
                re.IGNORECASE,
            ),
        ),
        (
            "JAILBREAK_ROLEPLAY",
            re.compile(
                r"(?:you\s+are\s+now\s+DAN|do\s+anything\s+now|developer\s+mode\s+active|jailbreak\s+mode|unrestricted\s+ai)",
                re.IGNORECASE,
            ),
        ),
        (
            "DELIMITER_HIJACK",
            re.compile(
                r"(?:<\|im_start\|>system|<system>|\[SYSTEM\s+INSTRUCTION\]|BEGIN\s+NEW\s+SYSTEM\s+PROMPT)",
                re.IGNORECASE,
            ),
        ),
    ]

    SUSPICIOUS_PATTERNS: ClassVar[list[tuple[str, re.Pattern]]] = [
        (
            "BASE64_EXECUTION",
            re.compile(
                r"(?:decode\s+this\s+base64\s+and\s+execute|base64:)", re.IGNORECASE
            ),
        ),
        (
            "HYPOTHETICAL_BYPASS",
            re.compile(
                r"(?:in\s+a\s+hypothetical\s+world\s+without\s+rules|pretend\s+you\s+have\s+no\s+safety\s+filters)",
                re.IGNORECASE,
            ),
        ),
    ]

    @classmethod
    def inspect(cls, text: str) -> InjectionCheckResult:
        """Analyze prompt for adversarial or jailbreak patterns."""
        if not text:
            return InjectionCheckResult()

        detected = []
        for name, pattern in cls.CRITICAL_PATTERNS:
            if pattern.search(text):
                detected.append(name)

        if detected:
            return InjectionCheckResult(
                is_safe=False,
                threat_level="CRITICAL",
                detected_patterns=detected,
                reason=f"Blocked prompt injection threat(s): {', '.join(detected)}",
            )

        suspicious = []
        for name, pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern.search(text):
                suspicious.append(name)

        if suspicious:
            return InjectionCheckResult(
                is_safe=False,
                threat_level="HIGH",
                detected_patterns=suspicious,
                reason=f"Suspicious prompt pattern detected: {', '.join(suspicious)}",
            )

        return InjectionCheckResult(
            is_safe=True,
            threat_level="SAFE",
            detected_patterns=[],
            reason="Prompt evaluated as safe.",
        )
