"""The Solar Manager integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import SolarManagerClient
from .const import CONF_SMART_MANAGER_ID, DOMAIN
from .coordinator import (
    SolarManagerForecastCoordinator,
    SolarManagerRealtimeCoordinator,
    SolarManagerSensorCoordinator,
    SolarManagerStatisticsCoordinator,
    SolarManagerTariffCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solar Manager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    options = entry.options or entry.data
    username = options[CONF_USERNAME]
    password = options[CONF_PASSWORD]
    smid = options[CONF_SMART_MANAGER_ID]

    session = async_get_clientsession(hass)
    client = SolarManagerClient(session, username, password, smid)

    # Create and refresh all coordinators
    realtime_coord = SolarManagerRealtimeCoordinator(hass, client)
    statistics_coord = SolarManagerStatisticsCoordinator(hass, client)
    forecast_coord = SolarManagerForecastCoordinator(hass, client)
    tariff_coord = SolarManagerTariffCoordinator(hass, client)
    sensor_coord = SolarManagerSensorCoordinator(hass, client)

    # Initial refresh — realtime and statistics are mandatory
    await realtime_coord.async_config_entry_first_refresh()
    await statistics_coord.async_config_entry_first_refresh()

    # Optional coordinators: don't fail setup if they return empty data
    await forecast_coord.async_refresh()
    await tariff_coord.async_refresh()
    await sensor_coord.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "smid": smid,
        "realtime": realtime_coord,
        "statistics": statistics_coord,
        "forecast": forecast_coord,
        "tariff": tariff_coord,
        "sensors": sensor_coord,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for option updates (re-configure)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
