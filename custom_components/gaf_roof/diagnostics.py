"""Diagnostics for GAF Roof."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import GafConfigEntry

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GafConfigEntry
) -> dict[str, Any]:
    """Return redacted integration diagnostics."""
    devices = entry.runtime_data.coordinator.data.values()
    return {
        "entry": {
            CONF_USERNAME: "**REDACTED**",
            CONF_PASSWORD: "**REDACTED**",
        },
        "options": dict(entry.options),
        "last_update_success": entry.runtime_data.coordinator.last_update_success,
        "device_count": len(entry.runtime_data.coordinator.data),
        "device_schemas": [
            {
                "fields": sorted(device),
                "device_config_fields": sorted(
                    device.get("deviceConfig", {})
                    if isinstance(device.get("deviceConfig"), dict)
                    else []
                ),
            }
            for device in devices
        ],
    }
