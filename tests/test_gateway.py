import pytest
from src.gateway.litellm_client import LiteLLMGateway, GatewayResponse

def test_gateway_fallback_and_telemetry():
    gateway = LiteLLMGateway(
        primary_model="nonexistent/primary-model",
        fallback_models=["nonexistent/secondary-model"],
        enable_mock_fallback=True
    )
    
    response = gateway.generate(
        messages=[{"role": "user", "content": "Check cluster health and memory consumption."}],
        agent_name="TestDiagnosticAgent",
        correlation_id="corr-gw-001"
    )
    
    assert isinstance(response, GatewayResponse)
    assert response.correlation_id == "corr-gw-001"
    assert response.fallback_occurred is True
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.total_tokens == response.prompt_tokens + response.completion_tokens
    assert response.latency_ms > 0
    assert "OFFLINE MOCK RESPONSE" in response.content

@pytest.mark.asyncio
async def test_async_gateway_fallback():
    gateway = LiteLLMGateway(
        primary_model="nonexistent/primary-model",
        fallback_models=["nonexistent/secondary-model"],
        enable_mock_fallback=True
    )
    
    response = await gateway.agenerate(
        messages=[{"role": "user", "content": "Async audit check."}],
        agent_name="AsyncAgent",
        correlation_id="corr-async-001"
    )
    
    assert response.correlation_id == "corr-async-001"
    assert response.fallback_occurred is True
    assert response.total_tokens > 0
