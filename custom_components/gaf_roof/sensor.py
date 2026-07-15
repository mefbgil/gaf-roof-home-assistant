"""Sensor entities for GAF Roof."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GafConfigEntry
from .api import device_identifier, legacy_device_slug
from .const import DOMAIN
from .coordinator import GafDataUpdateCoordinator

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GafSensorDescription(SensorEntityDescription):
    """Describe a GAF sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS = (
    GafSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda device: device.get("deviceConfig", {}).get("setTemperature"),
    ),
    GafSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda device: device.get("deviceConfig", {}).get("setHumidity"),
    ),
    GafSensorDescription(
        key="signal",
        translation_key="signal",
        entity_registry_enabled_default=False,
        value_fn=lambda device: device.get("signalStrength"),
    ),
)


async def async_setup_entry(
    hass,
    entry: GafConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors and discover devices added after startup."""
    coordinator = entry.runtime_data.coordinator
    known: set[str] = set()

    def add_new_devices() -> None:
        entities: list[GafSensor] = []
        for identifier in coordinator.data:
            if identifier in known:
                continue
            known.add(identifier)
            entities.extend(
                GafSensor(coordinator, identifier, description)
                for description in SENSORS
            )
        if entities:
            async_add_entities(entities)

    add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))


class GafSensor(CoordinatorEntity[GafDataUpdateCoordinator], SensorEntity):
    """Representation of one GAF cloud value."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GafDataUpdateCoordinator,
        identifier: str,
        description: GafSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._identifier = identifier
        self.entity_description = description
        device = coordinator.data[identifier]
        legacy_slug = legacy_device_slug(device)
        self._attr_unique_id = f"{legacy_slug}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier(device))},
            manufacturer="GAF",
            model="Keen Home",
            name=str(device.get("deviceName") or "GAF Roof"),
        )

    @property
    def native_value(self) -> Any:
        """Return the latest value from coordinator memory."""
        device = self.coordinator.data.get(self._identifier)
        if device is None:
            return None
        value = self.entity_description.value_fn(device)
        if value in ("", "Unavailable"):
            return None
        return value

    @property
    def available(self) -> bool:
        """Report unavailable if the coordinator or device is unavailable."""
        return super().available and self._identifier in self.coordinator.data
