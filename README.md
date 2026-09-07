# Enterprise AI Agent Engine ⚡

Production-grade, multi-agent AI system combining **FastMCP**, **LiteLLM Gateway**, **Security Guardrails**, **LangGraph State Machine Orchestration**, and **Full Enterprise Telemetry (Splunk, Dynatrace APM, OpenTelemetry, JVM GC Tuning)**.

---

## 🏗️ Architecture Overview

```
                                  +-----------------------+
                                  |   User Prompt / API   |
                                  +-----------+-----------+
                                              |
                                              v
                              +-------------------------------+
                              |    Guardrail Interceptor      |  <-- PII Redaction &
                              |  (Injection & PII Defense)    |      Adversarial Defense
                              +---------------+---------------+
                                              |
                                              v
                              +-------------------------------+
                              |   LangGraph State Machine     |
                              |   (Intent Router & Nodes)     |
                              +---------------+---------------+
                                 /            |            \
                                v             v             v
                    +--------------+  +--------------+  +--------------+
                    |  Diagnostic  |  | Vectorless   |  |   General    |
                    |    Worker    |  |  RAG Worker  |  |    Worker    |
                    +-------+------+  +-------+------+  +-------+------+
                            |                 |                 |
                            v                 v                 v
                    +--------------------------------------------------+
                    |           FastMCP Tool Server (Python)           |
                    | • get_system_health() • fetch_enterprise_record()|
                    +-------------------------+------------------------+
                                              |
                                              v
                    +--------------------------------------------------+
                    |              LiteLLM Proxy Gateway               |
                    |   Ollama/Llama3 -> Gemini -> GPT-4o-mini -> Mock |
                    +-------------------------+------------------------+
                                              |
                       +----------------------+-----------------------+
                       |                                              |
                       v                                              v
        +-----------------------------+               +-------------------------------+
        |    Splunk JSON Logging      |               |     Dynatrace APM PurePath    |
        | • Tokens, Cost, Latencies   |               | • W3C Distributed Tracing     |
        | • Correlation IDs & Alerts  |               | • OpenTelemetry Collectors    |
        +-----------------------------+               +-------------------------------+
```

---

## 🚀 Quick Start with `uv`

### 1. Requirements
* Python 3.13+ (or 3.12+)
* `uv` package manager

### 2. Environment Setup
```bash
# Navigate to project
cd /Users/anthonyjoyner/Documents/Projects/enterprise-agent-engine

# Run the complete system demonstration
uv run python main.py

# Run specific LangGraph queries
uv run python main.py --graph "Analyze JVM memory and GC pauses on cluster"
uv run python main.py --graph "Fetch balance and compliance details for ACC-9021"

# Run automated guardrail benchmark evaluations
uv run python main.py --eval

# Run full test suite (23 tests)
uv run pytest -v
```

---

## 📦 Core Capabilities by Epic

### Epic 1: FastMCP & Safe Model Gateway (`HER-5` - Completed)
* **FastMCP Tool Server (`src/mcp/server.py`)**: Exposes host metrics, active Java/JVM service process scanner (`get_system_health`), deterministic structured data queries (`fetch_enterprise_record`), and audit logging (`record_audit_event`).
* **LiteLLM Gateway (`src/gateway/litellm_client.py`)**: Centralized proxy client routing across local Ollama, Gemini, Claude, and OpenAI with automatic multi-tier fallback, cost tracking, and token usage headers.

### Epic 2: Security Guardrails & Distributed Tracing (`HER-6` - Completed)
* **PII Redaction Engine (`src/guardrails/pii_redactor.py`)**: Real-time regex/pattern masking of emails, phone numbers, SSNs/tax IDs, credit cards, and API secrets.
* **Prompt Injection Defense (`src/guardrails/injection_detector.py`)**: Blocks instruction overrides, jailbreak roleplay, and system prompt leakage attempts.
* **Automated Benchmark Evaluations (`src/evals/guardrail_eval.py`)**: 10-test benchmark suite achieving **100.0% accuracy** with **0.07 ms average latency**.
* **Distributed Tracing (`src/tracing/langsmith_tracker.py`)**: LangSmith RunTrees with offline local span fallback.

### Epic 3: LangGraph Orchestration & Vectorless RAG (`HER-7` - Completed)
* **StateGraph Architecture (`src/orchestration/graph.py`)**: Stateful, typed `AgentState` workflow with conditional routing edges.
* **Vectorless RAG (`src/orchestration/nodes.py`)**: Deterministic relational lookup from graph/relational databases without vector embeddings.
* **Post-Execution Guardrail**: Inspects LLM generated output to ensure no leaked internal PII reaches end consumers.

### Epic 4: Enterprise Telemetry & Infrastructure Performance (`HER-8` - Completed)
* **Splunk Dashboards & Queries (`src/telemetry/splunk/`)**:
  * Production Simple XML Dashboard (`agent_telemetry_dashboard.xml`)
  * Production SPL queries for P50/P95/P99 latencies, token consumption, and threat alerts (`saved_queries.spl`).
* **Dynatrace APM & OpenTelemetry (`src/telemetry/dynatrace/`)**:
  * Collector config (`otel_collector_config.yaml`) routing to Dynatrace endpoints.
  * Python Tracer injecting W3C `traceparent` headers for distributed tracing to Spring Boot services (`ResilientFulfillmentService`).
* **JVM Tuning Reference & Profiling (`src/telemetry/jvm/`)**:
  * Production G1GC & Generational ZGC flags (`jvm-options-reference.env`).
  * Automated diagnostic tool (`profile_jvm_load.sh`) running `jcmd`, `jstat -gcutil`, `jstack`, and `jmap`.
* **High-Concurrency Stress Testing (`tests/test_performance_concurrency.py`)**:
  * 20 concurrent asynchronous agent calls with zero correlation ID collisions and P95 latency tracking.

---

## 🤖 Multica Platform Integration

The project is tracked in Multica under project **Enterprise AI Agent Engine** (`3e17788f-6126-4dde-a360-aa816022967f`) in workspace `hermes-acjoyner`.

```bash
# Check Multica issue board
multica issue list

# Inspect project details
multica project get 3e17788f-6126-4dde-a360-aa816022967f
```

---

## 🧪 Test Verification

Run all 23 unit, integration, and concurrency stress tests:
```bash
uv run pytest -v
============================= 23 passed in 18.62s ==============================
```
