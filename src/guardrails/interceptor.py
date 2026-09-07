"""Guardrail Interceptor combining PII redaction, prompt injection detection, and audit logging."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from src.guardrails.pii_redactor import PIIRedactor, RedactionResult
from src.guardrails.injection_detector import InjectionDetector, InjectionCheckResult
from src.telemetry.logger import get_logger
from src.mcp.server import record_audit_event

logger = get_logger("guardrail-interceptor")


class InterceptorDecision(BaseModel):
    """Decision object summarizing guardrail inspection results."""
    allowed: bool
    sanitized_prompt: str
    original_prompt: str
    pii_result: RedactionResult
    injection_result: InjectionCheckResult
    correlation_id: str
    block_reason: Optional[str] = None


class GuardrailInterceptor:
    """Enterprise middleware intercepting agent prompts and responses to enforce safety."""

    @classmethod
    def process_input(
        cls,
        prompt: str,
        correlation_id: Optional[str] = None,
        actor: str = "user",
    ) -> InterceptorDecision:
        """Inspect and sanitize input before it reaches LiteLLM or an Agent node."""
        corr_id = correlation_id or f"corr-guard-{uuid.uuid4().hex[:8]}"

        # Step 1: Detect Prompt Injection / Jailbreaks
        injection_result = InjectionDetector.inspect(prompt)
        if not injection_result.is_safe:
            logger.warning(
                "prompt_injection_blocked",
                correlation_id=corr_id,
                threat_level=injection_result.threat_level,
                detected_patterns=injection_result.detected_patterns,
                reason=injection_result.reason,
            )
            record_audit_event(
                event_type="PROMPT_INJECTION_BLOCKED",
                actor=actor,
                details=f"Blocked threat: {injection_result.reason}",
                severity="CRITICAL",
                correlation_id=corr_id,
            )
            return InterceptorDecision(
                allowed=False,
                sanitized_prompt="",
                original_prompt=prompt,
                pii_result=RedactionResult(original_text=prompt, sanitized_text=prompt),
                injection_result=injection_result,
                correlation_id=corr_id,
                block_reason=injection_result.reason,
            )

        # Step 2: Redact sensitive PII
        pii_result = PIIRedactor.redact(prompt)
        if pii_result.has_pii:
            logger.info(
                "pii_redaction_applied",
                correlation_id=corr_id,
                redactions_count=pii_result.redactions_count,
                redacted_types=pii_result.redacted_types,
            )
            record_audit_event(
                event_type="PII_REDACTED",
                actor=actor,
                details=f"Redacted {pii_result.redactions_count} items: {pii_result.redacted_types}",
                severity="WARNING",
                correlation_id=corr_id,
            )

        return InterceptorDecision(
            allowed=True,
            sanitized_prompt=pii_result.sanitized_text,
            original_prompt=prompt,
            pii_result=pii_result,
            injection_result=injection_result,
            correlation_id=corr_id,
            block_reason=None,
        )

    @classmethod
    def process_output(
        cls,
        content: str,
        correlation_id: Optional[str] = None,
        actor: str = "agent",
    ) -> str:
        """Inspect and sanitize agent responses to prevent sensitive data leakage."""
        corr_id = correlation_id or f"corr-guard-{uuid.uuid4().hex[:8]}"
        pii_result = PIIRedactor.redact(content)
        if pii_result.has_pii:
            logger.warning(
                "output_pii_redacted",
                correlation_id=corr_id,
                redactions_count=pii_result.redactions_count,
                redacted_types=pii_result.redacted_types,
            )
            record_audit_event(
                event_type="OUTPUT_PII_MASKED",
                actor=actor,
                details=f"Masked {pii_result.redactions_count} items in LLM response",
                severity="WARNING",
                correlation_id=corr_id,
            )
        return pii_result.sanitized_text
