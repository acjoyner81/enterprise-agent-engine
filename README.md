Markdown
# Enterprise AI Agent Engine ⚡

Production-grade, multi-agent AI system combining **FastMCP**, **LiteLLM Gateway**, **Security Guardrails**, **LangGraph State Machine Orchestration**, and **Full Enterprise Telemetry (Splunk, Dynatrace APM, OpenTelemetry, JVM GC Tuning)**.

---

## 🏗️ Architecture Overview

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
                | • query_resilient_fulfillment_data()             |
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

---

## 🚀 Quick Start

### 1. Requirements
* Python 3.13+ (or 3.12+)
* `uv` package manager
* Ollama (for local LLM execution)

### 2. Execution via Shell Script (`run_agent.sh`)

The system includes a wrapper script `run_agent.sh` that automatically verifies and starts local dependencies (Ollama) before running the agent graph engine.

```bash
# Make the wrapper script executable
chmod +x run_agent.sh

# Run default workflow query via wrapper script
./run_agent.sh

# Run custom prompt via wrapper script
./run_agent.sh "Execute fulfillment order for customer test@example.com"
./run_agent.sh "Fetch balance and compliance details for ACC-9021"
3. Execution via uv
You can also run commands directly using uv:

Bash
# Navigate to project directory
cd ~/Documents/Projects/enterprise-agent-engine

# Run the complete system demonstration
uv run python main.py

# Run specific LangGraph queries directly
uv run python main.py --graph "Analyze JVM memory and GC pauses on cluster"
uv run python main.py --graph "Fetch balance and compliance details for ACC-9021"

# Run automated guardrail benchmark evaluations
uv run python main.py --eval

# Run full test suite
uv run pytest -v
📦 Core Capabilities by Epic
Epic 1: FastMCP & Safe Model Gateway (HER-5 - Completed)
FastMCP Tool Server (src/mcp/server.py): Exposes host metrics, active Java/JVM service process scanner (get_system_health), deterministic structured data queries (fetch_enterprise_record), audit logging (record_audit_event), and ResilientFulfillmentService application telemetry (query_resilient_fulfillment_data).

LiteLLM Gateway (src/gateway/litellm_client.py): Centralized proxy client routing across local Ollama (llama3), Gemini, Claude, and OpenAI with automatic multi-tier fallback, cost tracking, and token usage headers.

Epic 2: Security Guardrails & Distributed Tracing (HER-6 - Completed)
PII Redaction Engine (src/guardrails/pii_redactor.py): Real-time regex/pattern masking of emails, phone numbers, SSNs/tax IDs, credit cards, and API secrets.

Prompt Injection Defense (src/guardrails/injection_detector.py): Blocks instruction overrides, jailbreak roleplay, and system prompt leakage attempts.

Automated Benchmark Evaluations (src/evals/guardrail_eval.py): 10-test benchmark suite achieving 100.0% accuracy with 0.07 ms average latency.

Distributed Tracing (src/tracing/langsmith_tracker.py): LangSmith RunTrees with offline local span fallback.

Epic 3: LangGraph Orchestration & Vectorless RAG (HER-7 - Completed)
StateGraph Architecture (src/orchestration/graph.py): Stateful, typed AgentState workflow with conditional routing edges.

Vectorless RAG (src/orchestration/nodes.py): Deterministic relational lookup from graph/relational databases without vector embeddings.

Post-Execution Guardrail: Inspects LLM generated output to ensure no leaked internal PII reaches end consumers.

Epic 4: Enterprise Telemetry & Infrastructure Performance (HER-8 - Completed)
Splunk Dashboards & Queries (src/telemetry/splunk/):

Production Simple XML Dashboard (agent_telemetry_dashboard.xml)

Production SPL queries for P50/P95/P99 latencies, token consumption, Splunk application event indexing, and threat alerts (saved_queries.spl).

Dynatrace APM & OpenTelemetry (src/telemetry/dynatrace/):

Collector config (otel_collector_config.yaml) routing to Dynatrace endpoints.

Python Tracer injecting W3C traceparent headers for distributed tracing to Spring Boot services (ResilientFulfillmentService).

JVM Tuning Reference & Profiling (src/telemetry/jvm/):

Production G1GC & Generational ZGC flags (jvm-options-reference.env).

Automated diagnostic tool (profile_jvm_load.sh) running jcmd, jstat -gcutil, jstack, and jmap.

High-Concurrency Stress Testing (tests/test_performance_concurrency.py):

20 concurrent asynchronous agent calls with zero correlation ID collisions and P95 latency tracking.

🤖 Multica Platform Integration
The project is tracked in Multica under project Enterprise AI Agent Engine (3e17788f-6126-4dde-a360-aa816022967f) in workspace hermes-acjoyner.

Bash
# Check Multica issue board
multica issue list

# Inspect project details
multica project get 3e17788f-6126-4dde-a360-aa816022967f
🧪 Test Verification
Run all unit, integration, tool, and concurrency stress tests:

Bash
uv run pytest -v
