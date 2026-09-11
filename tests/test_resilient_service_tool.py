# tests/test_resilient_service_tool.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp.resilient_service_tool import trigger_fulfillment_service


@pytest.mark.asyncio
async def test_trigger_fulfillment_service_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "SUCCESS", "order_id": "ORD-1234"}
    mock_response.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await trigger_fulfillment_service("ORD-1234", "corr-test-99")

    assert result["status"] == "SUCCESS"
