"""Async HTTP client for the Solar Manager cloud API."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from ..const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class SolarManagerApiError(Exception):
    """Raised when an API request fails."""


class SolarManagerAuthError(SolarManagerApiError):
    """Raised on authentication failure (401/403)."""


class SolarManagerClient:
    """Async wrapper around the Solar Manager REST API.

    Uses HTTP Basic Auth — no external dependencies beyond aiohttp,
    which is already bundled with Home Assistant.
    """

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str, smid: str) -> None:
        self._session = session
        self._auth = aiohttp.BasicAuth(username, password)
        self._smid = smid

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    async def get_gateway_stream(self) -> dict[str, Any]:
        """Real-time gateway data: PV, consumption, battery, grid."""
        return await self._get(f"/v1/stream/gateway/{self._smid}")

    async def get_statistics(self) -> dict[str, Any]:
        """Today's energy statistics (requires accuracy + date range)."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from_str = today_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        to_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return await self._get(
            f"/v1/statistics/gateways/{self._smid}",
            params={"accuracy": "low", "from": from_str, "to": to_str},
        )

    async def get_forecast(self) -> dict[str, Any]:
        """PV production forecast (today & tomorrow)."""
        return await self._get(f"/v1/forecast/gateways/{self._smid}")

    async def get_tariff(self) -> dict[str, Any]:
        """Current energy tariffs."""
        return await self._get(f"/v1/tariff/gateways/{self._smid}")

    async def get_tariff_dynamic(self) -> dict[str, Any]:
        """Current dynamic tariffs."""
        return await self._get(f"/v1/tariff/gateways/{self._smid}/dynamic")

    async def get_sensors(self) -> list[dict[str, Any]]:
        """List of all sensors/devices registered on the gateway."""
        result = await self._get(f"/v1/info/sensors/{self._smid}")
        if isinstance(result, list):
            return result
        return result.get("sensors", [])

    async def get_sensor_stream(self, sensor_id: str) -> dict[str, Any]:
        """Real-time data for a specific sensor/device."""
        return await self._get(f"/v1/stream/sensor/{self._smid}/{sensor_id}")

    async def get_strings(self) -> list[dict[str, Any]]:
        """PV string information."""
        result = await self._get(f"/v1/info/strings/{self._smid}")
        if isinstance(result, list):
            return result
        return result.get("strings", [])

    async def get_overview(self) -> dict[str, Any]:
        """Gateway overview information."""
        return await self._get(f"/v1/info/gateway/{self._smid}")

    # ------------------------------------------------------------------
    # Public control methods
    # ------------------------------------------------------------------

    async def set_battery_mode(self, mode: str, smid: str | None = None) -> None:
        """Set battery operating mode."""
        await self._put("/v1/control/battery/mode", {"smId": smid or self._smid, "mode": mode})

    async def set_inverter_mode(self, mode: str, smid: str | None = None) -> None:
        """Set inverter operating mode."""
        await self._put("/v1/control/inverter/mode", {"smId": smid or self._smid, "mode": mode})

    async def set_heatpump_mode(self, device_id: str, mode: str) -> None:
        """Set heat pump operating mode."""
        await self._put("/v1/control/heatpump/mode", {"deviceId": device_id, "mode": mode})

    async def set_ev_charger_mode(self, device_id: str, mode: str) -> None:
        """Set EV charger operating mode."""
        await self._put("/v1/control/car-charger/mode", {"deviceId": device_id, "mode": mode})

    async def set_v2x_mode(self, device_id: str, mode: str) -> None:
        """Set V2X car charger operating mode."""
        await self._put("/v1/control/v2x-car-charger/mode", {"deviceId": device_id, "mode": mode})

    async def set_water_heater_mode(self, device_id: str, mode: str) -> None:
        """Set water heater operating mode."""
        await self._put("/v1/control/water-heater/mode", {"deviceId": device_id, "mode": mode})

    async def set_smart_plug_mode(self, device_id: str, mode: str) -> None:
        """Turn smart plug on/off."""
        await self._put("/v1/control/smart-plug/mode", {"deviceId": device_id, "mode": mode})

    async def set_switch_mode(self, device_id: str, mode: str) -> None:
        """Toggle a switch device."""
        await self._put("/v1/control/switch/mode", {"deviceId": device_id, "mode": mode})

    # ------------------------------------------------------------------
    # Validation helper
    # ------------------------------------------------------------------

    async def validate_credentials(self) -> bool:
        """Return True if credentials are valid (performs a lightweight API call)."""
        try:
            await self.get_overview()
            return True
        except SolarManagerAuthError:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{API_BASE_URL}{path}"
        _LOGGER.debug("GET %s params=%s", url, params)
        try:
            async with self._session.get(url, auth=self._auth, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status in (401, 403):
                    raise SolarManagerAuthError(f"Authentication failed for {url} (HTTP {resp.status})")
                if not resp.ok:
                    text = await resp.text()
                    raise SolarManagerApiError(
                        f"API error {resp.status} for {url}: {text[:200]}"
                    )
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise SolarManagerApiError(f"Network error for {url}: {exc}") from exc

    async def _put(self, path: str, data: dict[str, Any]) -> Any:
        url = f"{API_BASE_URL}{path}"
        _LOGGER.debug("PUT %s  body=%s", url, data)
        try:
            async with self._session.put(url, auth=self._auth, json=data, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status in (401, 403):
                    raise SolarManagerAuthError(f"Authentication failed for {url} (HTTP {resp.status})")
                if not resp.ok:
                    text = await resp.text()
                    raise SolarManagerApiError(
                        f"API error {resp.status} for {url}: {text[:200]}"
                    )
                try:
                    return await resp.json()
                except Exception:
                    return {}
        except aiohttp.ClientError as exc:
            raise SolarManagerApiError(f"Network error for {url}: {exc}") from exc
