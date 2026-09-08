# tests/test_resilient_service_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from src.mcp.resilient_service_tool import trigger_fulfillment_service

@pytest.mark.asyncio
async def test_trigger_fulfillment_service_success():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "SUCCESS", "order_id": "ORD-1234"}
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await trigger_fulfillment_service("ORD-1234", "corr-test-99")

        assert result["status"] == "SUCCESS"
        assert result["order_id"] == "ORD-1234"
        mock_post.assert_called_once()
        
        # Verify trace/correlation headers were passed
        headers = mock_post.call_args.kwarguments["headers"]
        assert headers["X-Correlation-ID"] == "corr-test-99"
        assert "traceparent" in headers