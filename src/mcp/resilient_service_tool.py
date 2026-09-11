# src/mcp/resilient_service_tool.py
from typing import Any

import httpx

from src.telemetry.dynatrace.tracer import inject_w3c_trace_headers

# Docker container host mapping
RESILIENT_SERVICE_URL = "http://localhost:8080"


async def trigger_fulfillment_service(
    order_id: str, correlation_id: str
) -> dict[str, Any]:
    """
    Triggers the ResilientFulfillmentService Spring Boot container
    with W3C distributed trace propagation.
    """
    headers = {"X-Correlation-ID": correlation_id, "Content-Type": "application/json"}

    # Inject W3C traceparent headers for Dynatrace PurePath tracking
    inject_w3c_trace_headers(headers)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{RESILIENT_SERVICE_URL}/api/v1/fulfillment",
                json={"order_id": order_id},
                headers=headers,
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            return {"status": "FAILED", "error": str(err), "order_id": order_id}


# Alias for MCP server import compatibility
invoke_resilient_fulfillment = trigger_fulfillment_service
