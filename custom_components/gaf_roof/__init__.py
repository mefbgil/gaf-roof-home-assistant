"""GAF Roof integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GafApiClient
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, PLATFORMS
from .coordinator import GafDataUpdateCoordinator


@dataclass
class GafRuntimeData:
    """Runtime objects associated with one config entry."""

    client: GafApiClient
    coordinator: GafDataUpdateCoordinator


type GafConfigEntry = ConfigEntry[GafRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: GafConfigEntry) -> bool:
    """Set up GAF Roof from a config entry."""
    client = GafApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = GafDataUpdateCoordinator(
        hass,
        client,
        int(entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = GafRuntimeData(client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GafConfigEntry) -> bool:
    """Unload a GAF Roof config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: GafConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
