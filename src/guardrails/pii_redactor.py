"""PII Redaction Engine applying high-accuracy pattern matching to mask sensitive data."""

import re
from typing import Dict, List, Pattern, Tuple
from pydantic import BaseModel, Field

class RedactionResult(BaseModel):
    """Result of PII inspection and redaction."""
    original_text: str
    sanitized_text: str
    has_pii: bool = False
    redactions_count: int = 0
    redacted_types: List[str] = Field(default_factory=list)


class PIIRedactor:
    """Pre/post-execution guardrail redacting sensitive enterprise and personal data."""

    PATTERNS: List[Tuple[str, Pattern, str]] = [
        # API Keys & Secrets (OpenAI, OpenShift tokens, Bearer tokens)
        (
            "SECRET_TOKEN",
            re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|sha256~[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|Bearer\s+[A-Za-z0-9._~+/-]{20,})", re.IGNORECASE),
            "[REDACTED_SECRET]",
        ),
        # Email addresses
        (
            "EMAIL",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[REDACTED_EMAIL]",
        ),
        # Social Security Numbers (US SSN / ITIN / Tax ID)
        (
            "SSN",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[REDACTED_SSN]",
        ),
        # Credit Card Numbers (Visa, MasterCard, Amex, Discover)
        (
            "CREDIT_CARD",
            re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b"),
            "[REDACTED_CREDIT_CARD]",
        ),
        # Phone numbers (US / International E.164 variations)
        (
            "PHONE",
            re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
            "[REDACTED_PHONE]",
        ),
        # National ID / Aadhaar-like 12 digit sequences
        (
            "NATIONAL_ID",
            re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
            "[REDACTED_NATIONAL_ID]",
        ),
    ]

    @classmethod
    def redact(cls, text: str) -> RedactionResult:
        """Inspect text, mask sensitive patterns, and return sanitized output with audit metadata."""
        if not text:
            return RedactionResult(original_text="", sanitized_text="", has_pii=False)

        sanitized = text
        redacted_types = []
        total_count = 0

        for pii_type, pattern, placeholder in cls.PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                redacted_types.append(pii_type)
                total_count += len(matches)
                sanitized = pattern.sub(placeholder, sanitized)

        return RedactionResult(
            original_text=text,
            sanitized_text=sanitized,
            has_pii=total_count > 0,
            redactions_count=total_count,
            redacted_types=list(set(redacted_types)),
        )
