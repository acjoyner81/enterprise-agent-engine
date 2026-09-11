# src/mcp/tools/synthetic_load.py

import os
import time
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize OpenTelemetry Tracer
tracer = trace.get_tracer("enterprise.agent.synthetic_load")

FULFILLMENT_SERVICE_URL = os.getenv(
    "FULFILLMENT_SERVICE_URL", "http://localhost:8080/api/v1/fulfillment"
)


def register_synthetic_load_tool(mcp: MCPServer) -> None:
    """Registers synthetic load generation tool on MCPServer instance."""

    @mcp.tool()
    async def inject_synthetic_fulfillment_load(
        order_count: int = 5,
        target_account_id: str = "ACC-9021",
        simulate_circuit_breaker: bool = False,
    ) -> dict[str, Any]:
        """
        Executes synthetic fulfillment requests against ResilientFulfillmentService,
        injecting W3C traceparent headers and custom correlation IDs.

        Args:
            order_count: Number of synthetic orders to generate (default 5).
            target_account_id: Account ID associated with the test transactions.
            simulate_circuit_breaker: Force high-latency / error flag to test fallback.
        """
        results = {
            "target_url": FULFILLMENT_SERVICE_URL,
            "requests_sent": order_count,
            "successful_requests": 0,
            "failed_requests": 0,
            "traces": [],
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(order_count):
                # Start an OTel span to generate W3C Context (traceparent)
                with tracer.start_as_current_span(
                    f"synthetic-fulfillment-step-{i + 1}"
                ) as span:
                    carrier: dict[str, str] = {}
                    TraceContextTextMapPropagator().inject(carrier)

                    correlation_id = (
                        f"synth-corr-{span.get_span_context().trace_id:032x}"
                    )

                    headers = {
                        **carrier,
                        "X-Correlation-ID": correlation_id,
                        "Content-Type": "application/json",
                    }

                    payload = {
                        "account_id": target_account_id,
                        "item_sku": f"SKU-{1000 + i}",
                        "quantity": 1,
                        "test_flag": True,
                        "force_failure": simulate_circuit_breaker and (i % 2 == 1),
                    }

                    start_time = time.perf_counter()
                    try:
                        response = await client.post(
                            f"{FULFILLMENT_SERVICE_URL}/process",
                            json=payload,
                            headers=headers,
                        )
                        latency_ms = (time.perf_counter() - start_time) * 1000

                        if response.status_code in (200, 201, 202):
                            results["successful_requests"] += 1
                            status = "SUCCESS"
                        else:
                            results["failed_requests"] += 1
                            status = f"HTTP_{response.status_code}"

                    except Exception as exc:  # noqa: BLE001
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        results["failed_requests"] += 1
                        status = f"ERROR: {type(exc).__name__}"

                    results["traces"].append(
                        {
                            "order_index": i + 1,
                            "traceparent": carrier.get("traceparent", "N/A"),
                            "correlation_id": correlation_id,
                            "latency_ms": round(latency_ms, 2),
                            "status": status,
                        }
                    )

        return results
