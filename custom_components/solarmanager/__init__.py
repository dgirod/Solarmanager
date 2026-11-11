"""The Solar Manager integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
    await sensor_coord.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "smid": smid,
        "realtime": realtime_coord,
        "statistics": statistics_coord,
        "forecast": forecast_coord,
        "tariff": tariff_coord,
        "sensors": sensor_coord,
    }

    # Register the gateway and all child devices up front and link them via
    # `via_device_id`. Platforms set up in parallel and the `via_device`
    # parameter in DeviceInfo is deprecated, so entities only reference the
    # devices by their identifiers.
    _async_register_devices(hass, entry, smid, sensor_coord.data or [])

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for option updates (re-configure)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


def _async_register_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    smid: str,
    sensors: list[dict],
) -> None:
    """Create the gateway device and attach every child device to it."""
    registry = dr.async_get(hass)
    gateway = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Solar Manager {smid}",
        manufacturer="Solar Manager AG",
        model="Solar Manager Gateway",
        configuration_url="https://solarmanager.ch",
    )
    for sensor in sensors:
        sensor_id = sensor.get("_id") or sensor.get("id", "")
        if not sensor_id:
            continue
        child = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{sensor_id}")},
            name=sensor.get("name") or sensor.get("type", sensor_id),
            manufacturer="Solar Manager AG",
            model=sensor.get("type", "Device"),
        )
        if child.via_device_id != gateway.id:
            registry.async_update_device(child.id, via_device_id=gateway.id)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
