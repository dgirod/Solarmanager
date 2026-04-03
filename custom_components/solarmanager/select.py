"""Select platform for Solar Manager — control operating modes."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.client import SolarManagerClient, SolarManagerApiError
from .const import (
    DOMAIN,
    BATTERY_MODES,
    INVERTER_MODES,
    HEATPUMP_MODES,
    EV_CHARGER_MODES,
    V2X_MODES,
    WATER_HEATER_MODES,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SolarManagerSelectDescription(SelectEntityDescription):
    """Select entity description including the API call to make."""
    options: list[str]
    set_fn: Callable[[SolarManagerClient, str], Awaitable[None]] | None = None


GATEWAY_SELECT_DESCRIPTIONS: tuple[SolarManagerSelectDescription, ...] = (
    SolarManagerSelectDescription(
        key="battery_mode",
        name="Battery Mode",
        icon="mdi:battery-charging-medium",
        options=BATTERY_MODES,
        set_fn=lambda client, mode: client.set_battery_mode(mode),
    ),
    SolarManagerSelectDescription(
        key="inverter_mode",
        name="Inverter Mode",
        icon="mdi:solar-power-variant",
        options=INVERTER_MODES,
        set_fn=lambda client, mode: client.set_inverter_mode(mode),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Solar Manager select entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SolarManagerClient = data["client"]
    smid: str = data["smid"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Solar Manager {smid}",
        manufacturer="Solar Manager AG",
        model="Solar Manager Gateway",
        configuration_url="https://solarmanager.ch",
    )

    entities: list[SelectEntity] = []

    # Gateway-level selects (battery, inverter)
    for desc in GATEWAY_SELECT_DESCRIPTIONS:
        entities.append(
            SolarManagerSelectEntity(client, desc, device_info, entry.entry_id)
        )

    # Device-specific selects built from sensor coordinator data
    sensor_coord = data["sensors"]
    for sensor in (sensor_coord.data or []):
        sensor_id = sensor.get("_id") or sensor.get("id", "")
        sensor_name = sensor.get("name") or sensor.get("type", sensor_id)
        sensor_type = (sensor.get("type") or "").lower()

        dev_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{sensor_id}")},
            name=sensor_name,
            manufacturer="Solar Manager AG",
            model=sensor.get("type", "Device"),
            via_device=(DOMAIN, entry.entry_id),
        )

        if "heatpump" in sensor_type:
            entities.append(SolarManagerSelectEntity(
                client,
                SolarManagerSelectDescription(
                    key=f"{sensor_id}_heatpump_mode",
                    name=f"{sensor_name} Mode",
                    icon="mdi:heat-pump",
                    options=HEATPUMP_MODES,
                    set_fn=lambda c, m, sid=sensor_id: c.set_heatpump_mode(sid, m),
                ),
                dev_info, entry.entry_id,
            ))

        elif "ev" in sensor_type or "car_charger" in sensor_type or "charger" in sensor_type:
            entities.append(SolarManagerSelectEntity(
                client,
                SolarManagerSelectDescription(
                    key=f"{sensor_id}_ev_mode",
                    name=f"{sensor_name} Mode",
                    icon="mdi:ev-station",
                    options=EV_CHARGER_MODES,
                    set_fn=lambda c, m, sid=sensor_id: c.set_ev_charger_mode(sid, m),
                ),
                dev_info, entry.entry_id,
            ))

        elif "v2x" in sensor_type:
            entities.append(SolarManagerSelectEntity(
                client,
                SolarManagerSelectDescription(
                    key=f"{sensor_id}_v2x_mode",
                    name=f"{sensor_name} Mode",
                    icon="mdi:car-electric",
                    options=V2X_MODES,
                    set_fn=lambda c, m, sid=sensor_id: c.set_v2x_mode(sid, m),
                ),
                dev_info, entry.entry_id,
            ))

        elif "water_heater" in sensor_type or "waterheater" in sensor_type:
            entities.append(SolarManagerSelectEntity(
                client,
                SolarManagerSelectDescription(
                    key=f"{sensor_id}_water_heater_mode",
                    name=f"{sensor_name} Mode",
                    icon="mdi:water-boiler",
                    options=WATER_HEATER_MODES,
                    set_fn=lambda c, m, sid=sensor_id: c.set_water_heater_mode(sid, m),
                ),
                dev_info, entry.entry_id,
            ))

    async_add_entities(entities)


class SolarManagerSelectEntity(SelectEntity):
    """Represents a Solar Manager operating mode selector."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: SolarManagerClient,
        description: SolarManagerSelectDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        self.entity_description = description
        self._client = client
        self._device_info = device_info
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_options = description.options
        self._attr_current_option = description.options[0]  # default: first option

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    async def async_select_option(self, option: str) -> None:
        """Change the selected option via API."""
        if self.entity_description.set_fn is None:
            return
        try:
            await self.entity_description.set_fn(self._client, option)
            self._attr_current_option = option
            self.async_write_ha_state()
        except SolarManagerApiError as err:
            _LOGGER.error("Failed to set %s to %s: %s", self.entity_description.key, option, err)
