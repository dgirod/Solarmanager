"""DataUpdateCoordinators for the Solar Manager integration."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
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
            stats = await self.client.get_statistics()
        except SolarManagerApiError as err:
            raise UpdateFailed(f"Statistics error: {err}") from err

        # Augment with daily energy breakdown (import/export/battery) from v3 range endpoint
        try:
            daily = await self.client.get_daily_energy()
            stats["gridPurchase"] = daily.get("iWh", 0.0)
            stats["gridFeedIn"] = daily.get("eWh", 0.0)
            stats["batteryDischarged"] = daily.get("bdWh", 0.0)
            stats["batteryCharged"] = daily.get("bcWh", 0.0)
        except SolarManagerApiError as err:
            _LOGGER.warning("Daily energy range data not available: %s", err)

        return stats


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
            raw = await self.client.get_forecast()
        except SolarManagerApiError as err:
            _LOGGER.warning("Forecast not available: %s", err)
            return {}
        try:
            return parse_forecast(raw)
        except (TypeError, ValueError, AttributeError) as err:
            _LOGGER.warning("Unexpected forecast format: %s", err)
            return {}


# ---------------------------------------------------------------------------
# Forecast parsing
# ---------------------------------------------------------------------------

_TS_KEYS = ("timestamp", "t", "time", "date", "datetime", "start")
_VALUE_KEYS = ("expected", "pW", "value", "power", "forecast", "p")


def _parse_ts(value: Any) -> datetime | None:
    """Convert an epoch (s or ms) or ISO string into an aware datetime."""
    if isinstance(value, (int, float)):
        if value > 1e11:  # milliseconds
            value = value / 1000
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        return dt_util.parse_datetime(value)
    return None


def _first(entry: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if entry.get(key) is not None:
            return entry[key]
    return None


def parse_forecast(raw: Any) -> dict[str, Any]:
    """Turn the forecast API response into {"today": Wh, "tomorrow": Wh}.

    The API returns a list of power values (W) with timestamps. Each value is
    multiplied by its interval length and summed up per local day.
    """
    if isinstance(raw, dict):
        if "today" in raw or "tomorrow" in raw:
            return raw
        raw = raw.get("data") or raw.get("forecast") or []
    if not isinstance(raw, list):
        return {}

    points: list[tuple[datetime, float]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        ts = _parse_ts(_first(entry, _TS_KEYS))
        val = _first(entry, _VALUE_KEYS)
        if ts is None or val is None:
            continue
        points.append((ts, float(val)))

    if not points:
        return {}
    points.sort(key=lambda p: p[0])

    # Each value counts until the next timestamp. The API may mix
    # resolutions (e.g. a first point at "now" followed by full hours),
    # so a single global interval would be wrong.
    gaps = [
        (b[0] - a[0]).total_seconds()
        for a, b in zip(points, points[1:])
        if b[0] > a[0]
    ]
    default_gap = sorted(gaps)[len(gaps) // 2] if gaps else 900  # median

    totals: dict[date, float] = {}
    for idx, (ts, power) in enumerate(points):
        if idx + 1 < len(points) and points[idx + 1][0] > ts:
            gap = (points[idx + 1][0] - ts).total_seconds()
            gap = min(gap, 2 * default_gap)  # don't bridge holes in the data
        else:
            gap = default_gap
        day = dt_util.as_local(ts).date()
        totals[day] = totals.get(day, 0.0) + power * gap / 3600

    today = dt_util.now().date()
    tomorrow = today + timedelta(days=1)
    return {
        "today": round(totals[today], 1) if today in totals else None,
        "tomorrow": round(totals[tomorrow], 1) if tomorrow in totals else None,
        "attributes": {
            "first_timestamp": dt_util.as_local(points[0][0]).isoformat(),
            "last_timestamp": dt_util.as_local(points[-1][0]).isoformat(),
            "points": len(points),
            "resolution_minutes": round(default_gap / 60, 1),
            "fields": sorted(raw[0].keys()) if raw and isinstance(raw[0], dict) else [],
        },
    }


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
