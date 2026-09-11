import pytest
from mcp.server.mcpserver import MCPServer

from src.mcp.tools.synthetic_load import register_synthetic_load_tool
from src.telemetry.dynatrace.tracer import verify_trace_ingestion


@pytest.mark.asyncio
async def test_synthetic_load_execution(httpx_mock):
    """Verifies synthetic load tool sends correct W3C traceparent headers."""
    # Allow the mock response to be used for multiple requests in the loop
    httpx_mock.add_response(
        url="http://localhost:8080/api/v1/fulfillment/process",
        status_code=200,
        json={"status": "ACCEPTED", "fulfillment_id": "FUL-1001"},
        is_reusable=True,
    )

    mcp = MCPServer("TestServer")
    register_synthetic_load_tool(mcp)

    tool = mcp._tool_manager.get_tool("inject_synthetic_fulfillment_load")
    assert tool is not None, (
        "Tool 'inject_synthetic_fulfillment_load' was not registered"
    )

    res = await tool.fn(order_count=2, target_account_id="ACC-9021")

    assert res["requests_sent"] == 2
    assert res["successful_requests"] == 2
    assert len(res["traces"]) == 2

    first_trace = res["traces"][0]
    assert "traceparent" in first_trace
    assert first_trace["correlation_id"].startswith("synth-corr-")


@pytest.mark.asyncio
async def test_dynatrace_verification_skipped_without_token(monkeypatch):
    """Ensures verify_trace_ingestion handles missing API keys gracefully."""
    monkeypatch.setenv("DT_API_TOKEN", "")
    res = await verify_trace_ingestion("4bf92f3577b34da6a3ce929d0e0e4736")
    assert res["status"] == "SKIPPED"
