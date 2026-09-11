"""Model Gateway Package integrating LiteLLM with fallback & telemetry."""

from .litellm_client import GatewayResponse, LiteLLMGateway

__all__ = ["GatewayResponse", "LiteLLMGateway"]
