"""Typed State schemas for LangGraph Multi-Agent Orchestrator."""

from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class StructuredOutputPayload(BaseModel):
    """Normalized structured response contract for enterprise downstream systems."""

    correlation_id: str
    route: str
    is_safe: bool
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    error: str | None = None


class AgentState(TypedDict):
    """Core state machine memory passed across LangGraph nodes."""

    correlation_id: str
    original_prompt: str
    sanitized_prompt: str
    is_safe: bool
    route: str  # "DIAGNOSTICS", "VECTORLESS_RAG", "GENERAL", "BLOCKED"
    error: str | None
    retry_count: int
    context_data: dict[str, Any]
    response_content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    execution_latency_ms: float
    structured_output: dict[str, Any] | None
