"""DataUpdateCoordinators for the Solar Manager integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import SolarManagerClient, SolarManagerApiError
from .const import (
    DOMAIN,
    SCAN_INTERVAL_REALTIME,
    SCAN_INTERVAL_STATISTICS,
    SCAN_INTERVAL_FORECAST,
    SCAN_INTERVAL_TARIFF,
    SCAN_INTERVAL_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


class SolarManagerRealtimeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for real-time gateway data (10 second updates)."""

    def __init__(self, hass: HomeAssistant, client: SolarManagerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_realtime",
            update_interval=timedelta(seconds=SCAN_INTERVAL_REALTIME),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_gateway_stream()
        except SolarManagerApiError as err:
            raise UpdateFailed(f"Gateway stream error: {err}") from err


class SolarManagerStatisticsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for daily energy statistics (5 minute updates)."""

    def __init__(self, hass: HomeAssistant, client: SolarManagerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_statistics",
            update_interval=timedelta(seconds=SCAN_INTERVAL_STATISTICS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_statistics()
        except SolarManagerApiError as err:
            raise UpdateFailed(f"Statistics error: {err}") from err


class SolarManagerForecastCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for PV production forecast (30 minute updates)."""

    def __init__(self, hass: HomeAssistant, client: SolarManagerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_forecast",
            update_interval=timedelta(seconds=SCAN_INTERVAL_FORECAST),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_forecast()
        except SolarManagerApiError as err:
            _LOGGER.warning("Forecast not available: %s", err)
            return {}


class SolarManagerTariffCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for energy tariff data (15 minute updates)."""

    def __init__(self, hass: HomeAssistant, client: SolarManagerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tariff",
            update_interval=timedelta(seconds=SCAN_INTERVAL_TARIFF),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.get_tariff()
            try:
                dynamic = await self.client.get_tariff_dynamic()
                data["dynamic"] = dynamic
            except SolarManagerApiError:
                data["dynamic"] = {}
            return data
        except SolarManagerApiError as err:
            _LOGGER.warning("Tariff data not available: %s", err)
            return {}


class SolarManagerSensorCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator for individual sensor/device data (30 second updates).

    First fetches the sensor list, then retrieves stream data for each sensor.
    Results are stored as a list of dicts with sensor info + current values merged.
    """

    def __init__(self, hass: HomeAssistant, client: SolarManagerClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_sensors",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SENSORS),
        )
        self.client = client
        self._sensor_ids: list[str] = []

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            sensors = await self.client.get_sensors()
        except SolarManagerApiError as err:
            _LOGGER.warning("Could not fetch sensor list: %s", err)
            return []

        results: list[dict[str, Any]] = []
        for sensor in sensors:
            sensor_id = sensor.get("_id") or sensor.get("id", "")
            if not sensor_id:
                continue
            enriched = dict(sensor)
            try:
                stream = await self.client.get_sensor_stream(sensor_id)
                enriched.update(stream)
            except SolarManagerApiError as err:
                _LOGGER.debug("Could not fetch stream for sensor %s: %s", sensor_id, err)
            results.append(enriched)

        return results
