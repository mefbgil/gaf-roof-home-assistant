"""Async client for the private GAF/Keen Home cloud API."""

from __future__ import annotations

import base64
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from .const import DEVICE_LIST_URL, LOGIN_URL, REQUEST_TIMEOUT, USER_POOL_ID, USER_ROLE


class GafApiError(Exception):
    """Base GAF API error."""


class GafAuthenticationError(GafApiError):
    """The GAF credentials were rejected."""


class GafConnectionError(GafApiError):
    """The GAF service could not be reached or returned invalid data."""


class GafApiClient:
    """Small async client with cached authentication."""

    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._timeout = ClientTimeout(total=REQUEST_TIMEOUT)

    async def async_authenticate(self) -> None:
        """Authenticate and cache an access token."""
        encoded_password = base64.b64encode(self._password.encode()).decode()
        payload = {
            "userName": self._username,
            "password": encoded_password,
            "userPoolId": USER_POOL_ID,
            "userRole": USER_ROLE,
        }

        try:
            async with self._session.post(
                LOGIN_URL, json=payload, timeout=self._timeout
            ) as response:
                if response.status in (400, 401, 403):
                    raise GafAuthenticationError("Invalid GAF credentials")
                response.raise_for_status()
                result = await response.json(content_type=None)
        except GafAuthenticationError:
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise GafConnectionError("Unable to authenticate with GAF") from err

        token = result.get("responseData", {}).get("accessToken")
        if not isinstance(token, str) or not token:
            raise GafAuthenticationError("GAF did not return an access token")
        self._access_token = token

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return the current GAF device list, refreshing auth once on 401."""
        if self._access_token is None:
            await self.async_authenticate()

        try:
            return await self._async_request_devices()
        except GafAuthenticationError:
            self._access_token = None
            await self.async_authenticate()
            return await self._async_request_devices()

    async def _async_request_devices(self) -> list[dict[str, Any]]:
        try:
            async with self._session.get(
                DEVICE_LIST_URL,
                headers={"authorization": self._access_token or ""},
                timeout=self._timeout,
            ) as response:
                if response.status in (401, 403):
                    raise GafAuthenticationError("GAF session expired")
                response.raise_for_status()
                result = await response.json(content_type=None)
        except GafAuthenticationError:
            raise
        except ClientResponseError as err:
            raise GafConnectionError(
                f"GAF returned HTTP status {err.status}"
            ) from err
        except (ClientError, TimeoutError, ValueError) as err:
            raise GafConnectionError("Unable to fetch GAF devices") from err

        devices = result.get("responseData")
        if not isinstance(devices, list):
            raise GafConnectionError("GAF returned an unexpected device response")
        return [device for device in devices if isinstance(device, dict)]


def device_identifier(device: dict[str, Any]) -> str:
    """Return the best stable identifier exposed by the cloud response."""
    for key in (
        "deviceId",
        "deviceID",
        "serialNumber",
        "serial_number",
        "uuid",
        "id",
    ):
        value = device.get(key)
        if value not in (None, ""):
            return str(value)
    return legacy_device_slug(device)


def legacy_device_slug(device: dict[str, Any]) -> str:
    """Match the identifier format used by the former MQTT bridge."""
    return str(device.get("deviceName") or "unknown").lower().replace(" ", "_")
