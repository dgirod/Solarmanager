"""Switch platform for Solar Manager — smart plugs and switches."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api.client import SolarManagerClient, SolarManagerApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Solar Manager switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SolarManagerClient = data["client"]
    sensor_coord = data["sensors"]
    entry_id = entry.entry_id

    entities: list[SwitchEntity] = []

    for sensor in (sensor_coord.data or []):
        sensor_id = sensor.get("_id") or sensor.get("id", "")
        sensor_name = sensor.get("name") or sensor.get("type", sensor_id)
        sensor_type = (sensor.get("type") or "").lower()

        dev_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{sensor_id}")},
            name=sensor_name,
            manufacturer="Solar Manager AG",
            model=sensor.get("type", "Device"),
            via_device=(DOMAIN, entry_id),
        )

        if "smart_plug" in sensor_type or "smartplug" in sensor_type:
            entities.append(
                SolarManagerSmartPlugSwitch(
                    client, sensor_id, sensor_name, dev_info, entry_id,
                    is_on=bool(sensor.get("switchState", 0)),
                    control_fn=lambda c, sid, m: c.set_smart_plug_mode(sid, m),
                )
            )

        elif "switch" in sensor_type:
            entities.append(
                SolarManagerSmartPlugSwitch(
                    client, sensor_id, sensor_name, dev_info, entry_id,
                    is_on=bool(sensor.get("switchState", 0)),
                    control_fn=lambda c, sid, m: c.set_switch_mode(sid, m),
                )
            )

    async_add_entities(entities)


class SolarManagerSmartPlugSwitch(SwitchEntity):
    """Represents a Solar Manager smart plug or switch."""

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(
        self,
        client: SolarManagerClient,
        sensor_id: str,
        name: str,
        device_info: DeviceInfo,
        entry_id: str,
        is_on: bool,
        control_fn,
    ) -> None:
        self._client = client
        self._sensor_id = sensor_id
        self._attr_name = name
        self._device_info = device_info
        self._attr_unique_id = f"{entry_id}_{sensor_id}_switch"
        self._attr_is_on = is_on
        self._control_fn = control_fn

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    async def async_turn_on(self, **kwargs) -> None:
        try:
            await self._control_fn(self._client, self._sensor_id, "on")
            self._attr_is_on = True
            self.async_write_ha_state()
        except SolarManagerApiError as err:
            _LOGGER.error("Failed to turn on %s: %s", self._sensor_id, err)

    async def async_turn_off(self, **kwargs) -> None:
        try:
            await self._control_fn(self._client, self._sensor_id, "off")
            self._attr_is_on = False
            self.async_write_ha_state()
        except SolarManagerApiError as err:
            _LOGGER.error("Failed to turn off %s: %s", self._sensor_id, err)
