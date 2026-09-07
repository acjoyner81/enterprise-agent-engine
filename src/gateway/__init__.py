"""Model Gateway Package integrating LiteLLM with fallback & telemetry."""

from .litellm_client import LiteLLMGateway, GatewayResponse

__all__ = ["LiteLLMGateway", "GatewayResponse"]
