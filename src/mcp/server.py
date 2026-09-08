"""FastMCP Tool Server exposing system telemetry, vectorless data retrieval, and audit logging."""

import datetime
import os
import platform
import psutil
from typing import Any, Dict, Optional
from fastmcp import FastMCP
from src.telemetry.logger import get_logger
from src.mcp.resilient_service_tool import invoke_resilient_fulfillment

logger = get_logger("mcp-server")

# Initialize FastMCP Server
mcp = FastMCP("enterprise-telemetry-server")

# Mock Enterprise Graph/Relational Data Store for Vectorless RAG
ENTERPRISE_DATABASE: Dict[str, Dict[str, Any]] = {
    "ACC-9021": {
        "id": "ACC-9021",
        "entity": "Global Wealth Partners",
        "tier": "Enterprise Platinum",
        "region": "us-east-1",
        "compliance_status": "COMPLIANT",
        "balance_usd": 1450000.00,
        "primary_contact": "alex.morgan@gwp-example.com",
        "linked_services": ["ResilientFulfillmentService", "KafkaEventStream", "DynatraceAgent"],
        "last_audit": "2026-08-15T10:00:00Z",
    },
    "ACC-4042": {
        "id": "ACC-4042",
        "entity": "FinTech Core Systems",
        "tier": "Standard Business",
        "region": "us-west-2",
        "compliance_status": "REVIEW_PENDING",
        "balance_usd": 320500.00,
        "primary_contact": "sarah.connor@fintech-example.com",
        "linked_services": ["ResilientFulfillmentService"],
        "last_audit": "2026-07-20T14:30:00Z",
    },
}


@mcp.tool()
def get_system_health() -> Dict[str, Any]:
    """Retrieve host telemetry, memory usage, CPU stats, and active JVM/Java processes.

    Useful for diagnostic agents assessing node health, garbage collection impact,
    and enterprise service availability.
    """
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)

    # Scan for Java/JVM processes (e.g. Spring Boot, Kafka, OpenShift agents)
    jvm_processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info["name"] or ""
            cmdline = " ".join(proc.info["cmdline"] or [])
            if (
                "java" in name.lower()
                or "openjdk" in name.lower()
                or "spring" in cmdline.lower()
            ):
                jvm_processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": name,
                        "cmdline_summary": cmdline[:120] if cmdline else "",
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    telemetry = {
        "status": "HEALTHY" if mem.percent < 90 else "DEGRADED",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_usage_pct": psutil.cpu_percent(interval=None),
        "memory_total_mb": round(mem.total / (1024 * 1024), 2),
        "memory_used_mb": round(mem.used / (1024 * 1024), 2),
        "memory_usage_pct": mem.percent,
        "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
        "load_average_1m": load_avg[0],
        "jvm_processes_detected": len(jvm_processes),
        "jvm_services": jvm_processes[:5],
    }

    logger.info(
        "system_health_queried",
        status=telemetry["status"],
        jvm_count=len(jvm_processes),
    )
    return telemetry


@mcp.tool()
def fetch_enterprise_record(
    record_id: str, record_type: str = "account"
) -> Dict[str, Any]:
    """Retrieve structured enterprise records by ID without vector similarity search.

    Implements deterministic Vectorless RAG retrieval from relational/graph records.

    Args:
        record_id: Unique record identifier (e.g., 'ACC-9021')
        record_type: Entity category (e.g., 'account', 'service', 'compliance')
    """
    logger.info(
        "fetch_enterprise_record_requested",
        record_id=record_id,
        record_type=record_type,
    )

    record = ENTERPRISE_DATABASE.get(record_id.strip())
    if not record:
        return {
            "found": False,
            "record_id": record_id,
            "message": f"Record '{record_id}' not found in enterprise relational store.",
        }

    return {
        "found": True,
        "record_id": record_id,
        "record_type": record_type,
        "data": record,
    }


@mcp.tool()
def record_audit_event(
    event_type: str,
    actor: str,
    details: str,
    severity: str = "INFO",
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Emit an enterprise audit trail event for compliance, Splunk logging, and security review.

    Args:
        event_type: Category of audit (e.g., 'TOOL_EXECUTION', 'PII_REDACTION', 'GATEWAY_ROUTING')
        actor: System user or agent identity performing the action
        details: Human/machine readable description of the event
        severity: Log severity level ('INFO', 'WARNING', 'CRITICAL')
        correlation_id: Tracing correlation ID for end-to-end request linking
    """
    payload = {
        "event_type": event_type,
        "actor": actor,
        "details": details,
        "severity": severity,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "correlation_id": correlation_id or "unassigned",
    }
    logger.info("audit_event_logged", **payload)
    return {"status": "RECORDED", "audit_record": payload}

@mcp.tool()
async def trigger_resilient_fulfillment(
    order_id: str, correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Trigger the ResilientFulfillmentService Spring Boot container via HTTP REST with W3C tracing.

    Args:
        order_id: Unique order ID to process
        correlation_id: Tracing correlation ID
    """
    logger.info("trigger_resilient_fulfillment_requested", order_id=order_id)
    return await invoke_resilient_fulfillment(
        order_id=order_id, correlation_id=correlation_id or "unassigned"
    )

if __name__ == "__main__":
    mcp.run()
