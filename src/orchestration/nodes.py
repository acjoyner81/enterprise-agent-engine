"""Node definitions for the LangGraph Multi-Agent State Machine."""

import re
from typing import Any

from src.gateway.litellm_client import LiteLLMGateway
from src.guardrails.interceptor import GuardrailInterceptor
from src.mcp.server import fetch_enterprise_record, get_system_health
from src.orchestration.state import AgentState, StructuredOutputPayload
from src.telemetry.logger import get_logger, log_llm_execution

logger = get_logger("graph-nodes")
gateway = LiteLLMGateway(primary_model="ollama/llama3", enable_mock_fallback=True)


def guardrail_node(state: AgentState) -> dict[str, Any]:
    """Inspect input for prompt injections and mask sensitive PII."""
    prompt = state.get("original_prompt", "")
    corr_id = state.get("correlation_id", "unassigned")

    decision = GuardrailInterceptor.process_input(prompt, correlation_id=corr_id)

    if not decision.allowed:
        return {
            "is_safe": False,
            "route": "BLOCKED",
            "error": decision.block_reason,
            "response_content": f"[SECURITY REFUSAL] Request blocked: {decision.block_reason}",
            "sanitized_prompt": "",
        }

    return {
        "is_safe": True,
        "sanitized_prompt": decision.sanitized_prompt,
        "error": None,
    }


def router_node(state: AgentState) -> dict[str, Any]:
    """Classify user intent to direct execution to specialized worker agents."""
    prompt_lower = state.get("sanitized_prompt", "").lower()

    if any(
        k in prompt_lower
        for k in [
            "health",
            "cpu",
            "memory",
            "jvm",
            "load",
            "gc",
            "system status",
            "diagnostic",
        ]
    ):
        route = "DIAGNOSTICS"
    elif re.search(r"\bacc-\d+\b", prompt_lower) or any(
        k in prompt_lower
        for k in ["account", "balance", "record", "client entity", "enterprise record"]
    ):
        route = "VECTORLESS_RAG"
    else:
        route = "GENERAL"

    logger.info(
        "intent_routed",
        correlation_id=state.get("correlation_id"),
        selected_route=route,
    )
    return {"route": route}


def diagnostic_worker_node(state: AgentState) -> dict[str, Any]:
    """Execute host and JVM diagnostics via FastMCP and generate an analysis report."""
    corr_id = state.get("correlation_id", "unassigned")
    prompt = state.get("sanitized_prompt", "")

    # Retrieve live host telemetry from FastMCP
    health_data = get_system_health()

    messages = [
        {
            "role": "system",
            "content": "You are an Enterprise Reliability Engineer. Given system telemetry and JVM metrics, provide concise diagnosis.",
        },
        {
            "role": "user",
            "content": f"User Request: {prompt}\n\nHost & JVM Telemetry Data:\n{health_data}",
        },
    ]

    resp = gateway.generate(
        messages=messages,
        agent_name="DiagnosticWorker",
        correlation_id=corr_id,
    )

    return {
        "context_data": health_data,
        "response_content": resp.content,
        "prompt_tokens": state.get("prompt_tokens", 0) + resp.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + resp.completion_tokens,
        "total_tokens": state.get("total_tokens", 0) + resp.total_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0) + resp.cost_usd,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0)
        + resp.latency_ms,
    }


def rag_worker_node(state: AgentState) -> dict[str, Any]:
    """Execute deterministic vectorless RAG lookup from structured store and parse output."""
    corr_id = state.get("correlation_id", "unassigned")
    prompt = state.get("sanitized_prompt", "")

    # Extract record ID or fallback to standard demo record
    match = re.search(r"\b(acc-\d+)\b", prompt, re.IGNORECASE)
    record_id = match.group(1).upper() if match else "ACC-9021"

    # Query structured database via FastMCP tool
    record_result = fetch_enterprise_record(record_id)

    messages = [
        {
            "role": "system",
            "content": "You are a financial enterprise knowledge agent. Synthesize the retrieved structured record to answer the user query accurately.",
        },
        {
            "role": "user",
            "content": f"User Request: {prompt}\n\nRetrieved Structured Record:\n{record_result}",
        },
    ]

    resp = gateway.generate(
        messages=messages,
        agent_name="VectorlessRAGWorker",
        correlation_id=corr_id,
    )

    return {
        "context_data": record_result,
        "response_content": resp.content,
        "prompt_tokens": state.get("prompt_tokens", 0) + resp.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + resp.completion_tokens,
        "total_tokens": state.get("total_tokens", 0) + resp.total_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0) + resp.cost_usd,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0)
        + resp.latency_ms,
    }


def general_worker_node(state: AgentState) -> dict[str, Any]:
    """Process general queries through LiteLLM Gateway."""
    corr_id = state.get("correlation_id", "unassigned")
    prompt = state.get("sanitized_prompt", "")

    messages = [
        {
            "role": "system",
            "content": "You are a helpful enterprise AI assistant.",
        },
        {"role": "user", "content": prompt},
    ]

    resp = gateway.generate(
        messages=messages,
        agent_name="GeneralWorker",
        correlation_id=corr_id,
    )

    return {
        "context_data": {},
        "response_content": resp.content,
        "prompt_tokens": state.get("prompt_tokens", 0) + resp.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + resp.completion_tokens,
        "total_tokens": state.get("total_tokens", 0) + resp.total_tokens,
        "total_cost_usd": state.get("total_cost_usd", 0.0) + resp.cost_usd,
        "execution_latency_ms": state.get("execution_latency_ms", 0.0)
        + resp.latency_ms,
    }


def output_formatter_node(state: AgentState) -> dict[str, Any]:
    """Sanitize output, construct structured Pydantic payload, and emit end-to-end metrics."""
    corr_id = state.get("correlation_id", "unassigned")
    raw_content = state.get("response_content", "")

    # Post-execution PII protection guardrail
    sanitized_output = GuardrailInterceptor.process_output(
        raw_content, correlation_id=corr_id
    )

    payload = StructuredOutputPayload(
        correlation_id=corr_id,
        route=state.get("route", "UNKNOWN"),
        is_safe=state.get("is_safe", True),
        content=sanitized_output,
        data=state.get("context_data", {}),
        prompt_tokens=state.get("prompt_tokens", 0),
        completion_tokens=state.get("completion_tokens", 0),
        total_tokens=state.get("total_tokens", 0),
        cost_usd=round(state.get("total_cost_usd", 0.0), 6),
        latency_ms=round(state.get("execution_latency_ms", 0.0), 2),
        error=state.get("error"),
    )

    log_llm_execution(
        logger,
        correlation_id=corr_id,
        agent_name="LangGraphEngine",
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        execution_time_ms=payload.latency_ms,
        model_name="langgraph-multi-agent",
        status="BLOCKED" if not payload.is_safe else "SUCCESS",
        cost_usd=payload.cost_usd,
        route=payload.route,
    )

    return {
        "response_content": sanitized_output,
        "structured_output": payload.model_dump(),
    }
