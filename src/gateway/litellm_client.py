"""LiteLLM Gateway routing client with automatic fallbacks and Splunk telemetry."""

import time
import uuid
from typing import Any

import litellm
from pydantic import BaseModel

from src.telemetry.logger import get_logger, log_llm_execution

logger = get_logger("litellm-gateway")

# Silence verbose litellm debug logs
litellm.suppress_debug_info = True


class GatewayResponse(BaseModel):
    """Normalized response payload containing model output and comprehensive usage telemetry."""

    content: str
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    correlation_id: str
    fallback_occurred: bool = False
    status: str = "SUCCESS"


class LiteLLMGateway:
    """Enterprise Gateway managing model invocations, fallbacks, and token tracking."""

    def __init__(
        self,
        primary_model: str = "ollama/llama3",
        fallback_models: list[str] | None = None,
        enable_mock_fallback: bool = True,
    ):
        self.primary_model = primary_model
        self.fallback_models = fallback_models or [
            "gemini/gemini-2.5-flash",
            "gpt-4o-mini",
        ]
        self.enable_mock_fallback = enable_mock_fallback

    def generate(
        self,
        messages: list[dict[str, str]],
        agent_name: str = "EnterpriseAgent",
        correlation_id: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> GatewayResponse:
        """Synchronous model call with fallback progression and telemetry logging."""
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
        models_to_try = [self.primary_model] + self.fallback_models
        fallback_occurred = False
        last_error = None

        for idx, model in enumerate(models_to_try):
            if idx > 0:
                fallback_occurred = True
                logger.warning(
                    "attempting_model_fallback",
                    correlation_id=corr_id,
                    primary_model=self.primary_model,
                    fallback_target=model,
                    error=str(last_error),
                )

            start_time = time.perf_counter()
            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Extract usage metadata
                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                completion_tokens = (
                    getattr(usage, "completion_tokens", 0) if usage else 0
                )
                total_tokens = (
                    getattr(usage, "total_tokens", prompt_tokens + completion_tokens)
                    if usage
                    else 0
                )

                try:
                    cost_usd = (
                        litellm.completion_cost(completion_response=response) or 0.0
                    )
                except Exception:  # noqa: BLE001
                    cost_usd = 0.0

                content = response.choices[0].message.content or ""

                # Emit structured telemetry log (Splunk-ready)
                log_llm_execution(
                    logger,
                    correlation_id=corr_id,
                    agent_name=agent_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    execution_time_ms=latency_ms,
                    model_name=model,
                    status="SUCCESS",
                    cost_usd=cost_usd,
                    fallback_occurred=fallback_occurred,
                )

                return GatewayResponse(
                    content=content,
                    model_used=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    correlation_id=corr_id,
                    fallback_occurred=fallback_occurred,
                    status="SUCCESS",
                )

            except Exception as exc:  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "model_invocation_failed",
                    correlation_id=corr_id,
                    model_attempted=model,
                    error=str(exc),
                )
                continue

        # If all live endpoints failed and mock fallback is enabled
        if self.enable_mock_fallback:
            latency_ms = 45.0
            last_msg = messages[-1]["content"] if messages else "No content provided"
            mock_content = (
                f"[OFFLINE MOCK RESPONSE for {agent_name}] Processed request: "
                f"'{last_msg[:80]}...' (Fallback triggered due to: {last_error})"
            )
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2
            completion_tokens = len(mock_content.split()) * 2

            log_llm_execution(
                logger,
                correlation_id=corr_id,
                agent_name=agent_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                execution_time_ms=latency_ms,
                model_name="mock-offline-fallback",
                status="MOCK_FALLBACK",
                cost_usd=0.0,
                fallback_occurred=True,
            )

            return GatewayResponse(
                content=mock_content,
                model_used="mock-offline-fallback",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=0.0,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                fallback_occurred=True,
                status="MOCK_FALLBACK",
            )

        raise RuntimeError(
            f"All model endpoints failed in LiteLLMGateway. Last error: {last_error}"
        )

    async def agenerate(
        self,
        messages: list[dict[str, str]],
        agent_name: str = "EnterpriseAgent",
        correlation_id: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> GatewayResponse:
        """Async model call with fallback progression and telemetry logging."""
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
        models_to_try = [self.primary_model] + self.fallback_models
        fallback_occurred = False
        last_error = None

        for idx, model in enumerate(models_to_try):
            if idx > 0:
                fallback_occurred = True

            start_time = time.perf_counter()
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000

                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                completion_tokens = (
                    getattr(usage, "completion_tokens", 0) if usage else 0
                )
                total_tokens = (
                    getattr(usage, "total_tokens", prompt_tokens + completion_tokens)
                    if usage
                    else 0
                )

                try:
                    cost_usd = (
                        litellm.completion_cost(completion_response=response) or 0.0
                    )
                except Exception:  # noqa: BLE001
                    cost_usd = 0.0

                content = response.choices[0].message.content or ""

                log_llm_execution(
                    logger,
                    correlation_id=corr_id,
                    agent_name=agent_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    execution_time_ms=latency_ms,
                    model_name=model,
                    status="SUCCESS",
                    cost_usd=cost_usd,
                    fallback_occurred=fallback_occurred,
                )

                return GatewayResponse(
                    content=content,
                    model_used=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=latency_ms,
                    correlation_id=corr_id,
                    fallback_occurred=fallback_occurred,
                    status="SUCCESS",
                )
            except Exception as exc:  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001
                last_error = exc
                continue

        if self.enable_mock_fallback:
            latency_ms = 35.0
            last_msg = messages[-1]["content"] if messages else "No content provided"
            mock_content = (
                f"[OFFLINE MOCK RESPONSE for {agent_name}] Processed: {last_msg[:80]}"
            )
            prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2
            completion_tokens = len(mock_content.split()) * 2

            log_llm_execution(
                logger,
                correlation_id=corr_id,
                agent_name=agent_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                execution_time_ms=latency_ms,
                model_name="mock-offline-fallback",
                status="MOCK_FALLBACK",
                cost_usd=0.0,
                fallback_occurred=True,
            )

            return GatewayResponse(
                content=mock_content,
                model_used="mock-offline-fallback",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=0.0,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                fallback_occurred=True,
                status="MOCK_FALLBACK",
            )

        raise RuntimeError(
            f"All model endpoints failed in LiteLLMGateway. Last error: {last_error}"
        )
