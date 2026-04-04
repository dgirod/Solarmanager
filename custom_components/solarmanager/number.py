"""Number platform for Solar Manager — manually configurable tariff values."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Currency unit — CHF not in HA constants; use string directly
CURRENCY_CHF = "CHF/kWh"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Solar Manager number entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    smid: str = data["smid"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Solar Manager {smid}",
        manufacturer="Solar Manager AG",
        model="Solar Manager Gateway",
        configuration_url="https://solarmanager.ch",
    )

    async_add_entities([
        SolarManagerTariffNumber(
            entry_id=entry.entry_id,
            key="tariff_buy",
            name="Energy Tariff Buy",
            icon="mdi:cash-plus",
            device_info=device_info,
        ),
        SolarManagerTariffNumber(
            entry_id=entry.entry_id,
            key="tariff_sell",
            name="Energy Tariff Sell",
            icon="mdi:cash-minus",
            device_info=device_info,
        ),
    ])


class SolarManagerTariffNumber(RestoreEntity, NumberEntity):
    """Manually configurable energy tariff value (CHF/kWh).

    Uses RestoreEntity so the last-set value survives HA restarts.
    The user can edit the value directly in the Home Assistant UI.
    """

    _attr_has_entity_name = True
    _attr_native_min_value = 0.0
    _attr_native_max_value = 10.0
    _attr_native_step = 0.001
    _attr_native_unit_of_measurement = CURRENCY_CHF
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        entry_id: str,
        key: str,
        name: str,
        icon: str,
        device_info: DeviceInfo,
    ) -> None:
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._device_info = device_info
        self._attr_native_value: float = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    async def async_added_to_hass(self) -> None:
        """Restore the last value after HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        """Set a new tariff value."""
        self._attr_native_value = round(value, 3)
        self.async_write_ha_state()
