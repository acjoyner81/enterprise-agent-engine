"""LangGraph State Machine compiling and executing multi-agent workflows."""

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.orchestration.nodes import (
    diagnostic_worker_node,
    general_worker_node,
    guardrail_node,
    output_formatter_node,
    rag_worker_node,
    router_node,
)
from src.orchestration.state import AgentState, StructuredOutputPayload
from src.tracing.langsmith_tracker import DistributedTracer

tracer = DistributedTracer(project_name="enterprise-langgraph")


def route_guardrail_edge(state: AgentState) -> str:
    """Decide whether to proceed to router or abort to formatter on security violations."""
    if not state.get("is_safe", True):
        return "output_formatter"
    return "router"


def route_intent_edge(state: AgentState) -> str:
    """Route execution to the appropriate specialized worker node."""
    route = state.get("route", "GENERAL")
    if route == "DIAGNOSTICS":
        return "diagnostic_worker"
    elif route == "VECTORLESS_RAG":
        return "rag_worker"
    return "general_worker"


def build_enterprise_graph() -> Any:
    """Construct and compile the state graph."""
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("router", router_node)
    workflow.add_node("diagnostic_worker", diagnostic_worker_node)
    workflow.add_node("rag_worker", rag_worker_node)
    workflow.add_node("general_worker", general_worker_node)
    workflow.add_node("output_formatter", output_formatter_node)

    # Define Graph Edges
    workflow.add_edge(START, "guardrail")
    workflow.add_conditional_edges(
        "guardrail",
        route_guardrail_edge,
        {
            "output_formatter": "output_formatter",
            "router": "router",
        },
    )
    workflow.add_conditional_edges(
        "router",
        route_intent_edge,
        {
            "diagnostic_worker": "diagnostic_worker",
            "rag_worker": "rag_worker",
            "general_worker": "general_worker",
        },
    )
    workflow.add_edge("diagnostic_worker", "output_formatter")
    workflow.add_edge("rag_worker", "output_formatter")
    workflow.add_edge("general_worker", "output_formatter")
    workflow.add_edge("output_formatter", END)

    return workflow.compile()


# Singleton compiled graph instance
compiled_agent_graph = build_enterprise_graph()


def execute_agent_graph(
    prompt: str,
    correlation_id: str | None = None,
) -> StructuredOutputPayload:
    """Execute the multi-agent state graph end-to-end with distributed tracing."""
    corr_id = correlation_id or f"corr-graph-{uuid.uuid4().hex[:8]}"

    span = tracer.start_trace(
        name="LangGraphOrchestrator",
        run_type="chain",
        inputs={"prompt": prompt},
        correlation_id=corr_id,
    )

    initial_state: AgentState = {
        "correlation_id": corr_id,
        "original_prompt": prompt,
        "sanitized_prompt": prompt,
        "is_safe": True,
        "route": "PENDING",
        "error": None,
        "retry_count": 0,
        "context_data": {},
        "response_content": "",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "execution_latency_ms": 0.0,
        "structured_output": None,
    }

    try:
        final_state = compiled_agent_graph.invoke(initial_state)
        structured_data = final_state.get("structured_output") or {}
        payload = StructuredOutputPayload(**structured_data)
        tracer.end_span(span, outputs=payload.model_dump())
        return payload
    except Exception as exc:
        tracer.end_span(span, error=str(exc))
        raise
