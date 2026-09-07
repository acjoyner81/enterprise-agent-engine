import pytest
from src.mcp.server import mcp, get_system_health, fetch_enterprise_record, record_audit_event

def test_system_health_tool():
    health = get_system_health()
    assert health["status"] in ["HEALTHY", "DEGRADED"]
    assert health["cpu_count"] >= 1
    assert "memory_usage_pct" in health
    assert "platform" in health
    assert isinstance(health["jvm_services"], list)

def test_fetch_enterprise_record_found():
    record = fetch_enterprise_record("ACC-9021")
    assert record["found"] is True
    assert record["record_id"] == "ACC-9021"
    assert record["data"]["entity"] == "Global Wealth Partners"
    assert "ResilientFulfillmentService" in record["data"]["linked_services"]

def test_fetch_enterprise_record_not_found():
    record = fetch_enterprise_record("NON-EXISTENT-ID")
    assert record["found"] is False
    assert "not found" in record["message"].lower()

def test_record_audit_event():
    audit = record_audit_event(
        event_type="TEST_ACTION",
        actor="unit-tester",
        details="Executed automated verification suite",
        severity="INFO",
        correlation_id="corr-audit-001"
    )
    assert audit["status"] == "RECORDED"
    assert audit["audit_record"]["actor"] == "unit-tester"
    assert audit["audit_record"]["correlation_id"] == "corr-audit-001"

@pytest.mark.asyncio
async def test_fastmcp_registered_tools():
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "get_system_health" in tool_names
    assert "fetch_enterprise_record" in tool_names
    assert "record_audit_event" in tool_names
