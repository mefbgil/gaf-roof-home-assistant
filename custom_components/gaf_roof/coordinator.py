"""Data coordinator for GAF Roof."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GafApiClient, GafAuthenticationError, GafConnectionError, device_identifier
from .const import DOMAIN, update_interval

_LOGGER = logging.getLogger(__name__)


class GafDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch all roof devices in a single coordinated request."""

    def __init__(
        self, hass: HomeAssistant, client: GafApiClient, poll_interval: int
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=update_interval(poll_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.client.async_get_devices()
        except GafAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except GafConnectionError as err:
            raise UpdateFailed(str(err)) from err

        return {device_identifier(device): device for device in devices}
