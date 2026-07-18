"""Tests for the GAF API client retry behavior."""

import sys
from pathlib import Path
from types import ModuleType
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call, patch

COMPONENT_ROOT = Path(__file__).parents[1] / "custom_components"
aiohttp = ModuleType("aiohttp")
aiohttp.ClientError = type("ClientError", (Exception,), {})
aiohttp.ClientResponseError = type("ClientResponseError", (aiohttp.ClientError,), {})
aiohttp.ClientSession = object
aiohttp.ClientTimeout = lambda **kwargs: kwargs
custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(COMPONENT_ROOT)]
gaf_roof = ModuleType("custom_components.gaf_roof")
gaf_roof.__path__ = [str(COMPONENT_ROOT / "gaf_roof")]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.gaf_roof", gaf_roof)
sys.modules.setdefault("aiohttp", aiohttp)

from custom_components.gaf_roof.api import (
    GafApiClient,
    GafAuthenticationError,
    GafConnectionError,
)


class GafApiClientRetryTests(IsolatedAsyncioTestCase):
    """Verify retries distinguish transient failures from permanent ones."""

    def setUp(self) -> None:
        """Create a client whose HTTP session is not used directly."""
        self.client = GafApiClient(AsyncMock(), "user", "password")
        self.client._access_token = "token"

    async def test_transient_failure_retries_with_exponential_backoff(self) -> None:
        """Transient failures retry twice before succeeding."""
        self.client._async_request_devices = AsyncMock(
            side_effect=[
                GafConnectionError("timeout"),
                GafConnectionError("invalid JSON"),
                [{"deviceId": "roof"}],
            ]
        )

        with patch(
            "custom_components.gaf_roof.api.asyncio.sleep", AsyncMock()
        ) as sleep:
            result = await self.client.async_get_devices()

        self.assertEqual(result, [{"deviceId": "roof"}])
        self.assertEqual(self.client._async_request_devices.await_count, 3)
        self.assertEqual(sleep.await_args_list, [call(1.0), call(2.0)])

    async def test_non_retryable_failure_fails_immediately(self) -> None:
        """Permanent HTTP failures do not retry."""
        error = GafConnectionError("HTTP 404", retryable=False)
        self.client._async_request_devices = AsyncMock(side_effect=error)

        with self.assertRaisesRegex(GafConnectionError, "HTTP 404"):
            await self.client.async_get_devices()

        self.client._async_request_devices.assert_awaited_once()

    async def test_authentication_refresh_does_not_back_off(self) -> None:
        """An expired token refreshes once without treating auth as transient."""
        self.client._access_token = "expired"
        self.client._async_request_devices = AsyncMock(
            side_effect=[GafAuthenticationError("expired"), [{"deviceId": "roof"}]]
        )

        async def authenticate() -> None:
            self.client._access_token = "fresh"

        self.client.async_authenticate = AsyncMock(side_effect=authenticate)

        result = await self.client.async_get_devices()

        self.assertEqual(result, [{"deviceId": "roof"}])
        self.client.async_authenticate.assert_awaited_once()
