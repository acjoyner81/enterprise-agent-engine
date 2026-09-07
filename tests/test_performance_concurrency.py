import asyncio
import time
import pytest
from src.gateway.litellm_client import LiteLLMGateway
from src.orchestration.graph import execute_agent_graph
from src.telemetry.dynatrace.tracer import DynatraceAgentTracer

@pytest.mark.asyncio
async def test_concurrent_agent_gateway_stress():
    """Simulate high concurrent load on the model gateway and verify correlation integrity."""
    gateway = LiteLLMGateway(primary_model="nonexistent/load-test", enable_mock_fallback=True)
    concurrency_count = 20

    async def single_agent_task(idx: int):
        corr_id = f"corr-stress-{idx:03d}"
        t0 = time.perf_counter()
        resp = await gateway.agenerate(
            messages=[{"role": "user", "content": f"Execute load query #{idx} for fulfillment cluster."}],
            agent_name=f"StressAgent-{idx}",
            correlation_id=corr_id
        )
        t_ms = (time.perf_counter() - t0) * 1000
        return resp, t_ms

    start_batch = time.perf_counter()
    results = await asyncio.gather(*[single_agent_task(i) for i in range(concurrency_count)])
    total_batch_ms = (time.perf_counter() - start_batch) * 1000

    # Verification
    assert len(results) == concurrency_count
    correlation_ids = set()
    latencies = []

    for resp, latency in results:
        assert resp.status in ["SUCCESS", "MOCK_FALLBACK"]
        assert resp.total_tokens > 0
        correlation_ids.add(resp.correlation_id)
        latencies.append(latency)

    # Verify zero correlation collisions across concurrent tasks
    assert len(correlation_ids) == concurrency_count

    # Calculate P95 latency
    latencies.sort()
    p95_index = int(concurrency_count * 0.95)
    p95_latency = latencies[p95_index]
    assert p95_latency > 0

def test_dynatrace_w3c_trace_headers_injection():
    """Verify W3C traceparent header injection for distributed tracing to Spring Boot."""
    headers = {"X-Client-Id": "agent-engine-01"}
    injected = DynatraceAgentTracer.inject_w3c_trace_headers(headers)
    
    assert "X-Client-Id" in injected
    # W3C traceparent header format: 00-{trace_id}-{span_id}-{trace_flags}
    assert "traceparent" in injected
    parts = injected["traceparent"].split("-")
    assert len(parts) == 4
    assert parts[0] == "00"  # Version
    assert len(parts[1]) == 32  # Trace ID
    assert len(parts[2]) == 16  # Span ID
