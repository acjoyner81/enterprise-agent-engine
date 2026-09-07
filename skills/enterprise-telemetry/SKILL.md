---
name: enterprise-telemetry
description: High-performance diagnostic tools, vectorless RAG retrieval, PII sanitization guardrails, and Splunk telemetry logging for autonomous AI agents.
---

# Enterprise Telemetry & Guardrail Skill

This skill equips agents with enterprise diagnostic, data retrieval, and guardrail capabilities built on FastMCP and LiteLLM.

## Capabilities

1. **System & JVM Diagnostics** (`get_system_health`):
   - Returns host CPU usage, memory utilization, disk space, and actively running JVM/Spring Boot services.
2. **Vectorless RAG Retrieval** (`fetch_enterprise_record`):
   - Performs deterministic entity and account lookups across relational/graph databases without vector embeddings.
3. **Audit Event Logging** (`record_audit_event`):
   - Logs security and agent compliance events directly into structured Splunk JSON format with correlation IDs.
4. **PII Sanitization & Prompt Injection Guardrails**:
   - Redacts emails, phone numbers, SSNs, credit cards, and secret tokens.
   - Blocks prompt injection, delimiter hijacking, and jailbreak attempts before reaching models.

## Usage from CLI

```bash
# Run full diagnostic and guardrail checks
uv run python main.py

# Run benchmark evaluations
uv run python main.py --eval

# Start stdio FastMCP Server
uv run python main.py --serve-mcp
```
