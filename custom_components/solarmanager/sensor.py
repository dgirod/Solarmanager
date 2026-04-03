"""Sensor platform for the Solar Manager integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    SolarManagerForecastCoordinator,
    SolarManagerRealtimeCoordinator,
    SolarManagerSensorCoordinator,
    SolarManagerStatisticsCoordinator,
    SolarManagerTariffCoordinator,
)

_LOGGER = logging.getLogger(__name__)

# Currency unit — CHF not in HA constants; use string directly
CURRENCY_CHF = "CHF/kWh"


# ---------------------------------------------------------------------------
# Entity description helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class SolarManagerSensorDescription(SensorEntityDescription):
    """Sensor description with an optional value path."""
    value_path: str | None = None  # dot-separated path into coordinator data


# ---------------------------------------------------------------------------
# Gateway real-time sensor descriptions
# ---------------------------------------------------------------------------

REALTIME_SENSOR_DESCRIPTIONS: tuple[SolarManagerSensorDescription, ...] = (
    SolarManagerSensorDescription(
        key="currentPvGeneration",
        name="PV Generation",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
    ),
    SolarManagerSensorDescription(
        key="currentPowerConsumption",
        name="Power Consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),
    SolarManagerSensorDescription(
        key="currentBatteryChargeDischarge",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    SolarManagerSensorDescription(
        key="currentGridPower",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    SolarManagerSensorDescription(
        key="soc",
        name="Battery State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    # Derived: grid import (positive grid power = buying from grid)
    SolarManagerSensorDescription(
        key="gridImportPower",
        name="Grid Import Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
    ),
    # Derived: grid export (negative grid power = selling to grid)
    SolarManagerSensorDescription(
        key="gridExportPower",
        name="Grid Export Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
    ),
    # Derived: self consumption power
    SolarManagerSensorDescription(
        key="selfConsumptionPower",
        name="Self Consumption Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-circle",
    ),
)

# ---------------------------------------------------------------------------
# Statistics sensor descriptions
# ---------------------------------------------------------------------------

STATISTICS_SENSOR_DESCRIPTIONS: tuple[SolarManagerSensorDescription, ...] = (
    SolarManagerSensorDescription(
        key="production",
        name="Daily PV Production",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-panel-large",
    ),
    SolarManagerSensorDescription(
        key="consumption",
        name="Daily Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt-outline",
    ),
    SolarManagerSensorDescription(
        key="selfConsumption",
        name="Daily Self Consumption",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-circle-outline",
    ),
    SolarManagerSensorDescription(
        key="selfConsumptionRate",
        name="Self Consumption Rate",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent-circle",
    ),
    SolarManagerSensorDescription(
        key="autarchyDegree",
        name="Autarchy Degree",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:shield-solar",
    ),
    SolarManagerSensorDescription(
        key="gridFeedIn",
        name="Daily Grid Feed-In",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
    ),
    SolarManagerSensorDescription(
        key="gridPurchase",
        name="Daily Grid Purchase",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
    ),
    SolarManagerSensorDescription(
        key="batteryDischarged",
        name="Daily Battery Discharged",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-minus",
    ),
    SolarManagerSensorDescription(
        key="batteryCharged",
        name="Daily Battery Charged",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-plus",
    ),
)

# ---------------------------------------------------------------------------
# Forecast sensor descriptions
# ---------------------------------------------------------------------------

FORECAST_SENSOR_DESCRIPTIONS: tuple[SolarManagerSensorDescription, ...] = (
    SolarManagerSensorDescription(
        key="today",
        name="PV Forecast Today",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-sunny",
    ),
    SolarManagerSensorDescription(
        key="tomorrow",
        name="PV Forecast Tomorrow",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-partly-cloudy",
    ),
)

# ---------------------------------------------------------------------------
# Tariff sensor descriptions
# ---------------------------------------------------------------------------

TARIFF_SENSOR_DESCRIPTIONS: tuple[SolarManagerSensorDescription, ...] = (
    SolarManagerSensorDescription(
        key="buy",
        name="Energy Tariff Buy",
        native_unit_of_measurement=CURRENCY_CHF,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cash-plus",
    ),
    SolarManagerSensorDescription(
        key="sell",
        name="Energy Tariff Sell",
        native_unit_of_measurement=CURRENCY_CHF,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cash-minus",
    ),
)


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Solar Manager sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    realtime_coord: SolarManagerRealtimeCoordinator = data["realtime"]
    statistics_coord: SolarManagerStatisticsCoordinator = data["statistics"]
    forecast_coord: SolarManagerForecastCoordinator = data["forecast"]
    tariff_coord: SolarManagerTariffCoordinator = data["tariff"]
    sensor_coord: SolarManagerSensorCoordinator = data["sensors"]

    smid: str = data["smid"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Solar Manager {smid}",
        manufacturer="Solar Manager AG",
        model="Solar Manager Gateway",
        configuration_url="https://solarmanager.ch",
    )

    entities: list[SensorEntity] = []

    # Real-time gateway sensors
    for desc in REALTIME_SENSOR_DESCRIPTIONS:
        entities.append(
            SolarManagerRealtimeSensor(realtime_coord, desc, device_info, entry.entry_id)
        )

    # Statistics sensors
    for desc in STATISTICS_SENSOR_DESCRIPTIONS:
        entities.append(
            SolarManagerStatisticsSensor(statistics_coord, desc, device_info, entry.entry_id)
        )

    # Forecast sensors
    for desc in FORECAST_SENSOR_DESCRIPTIONS:
        entities.append(
            SolarManagerForecastSensor(forecast_coord, desc, device_info, entry.entry_id)
        )

    # Tariff sensors
    for desc in TARIFF_SENSOR_DESCRIPTIONS:
        entities.append(
            SolarManagerTariffSensor(tariff_coord, desc, device_info, entry.entry_id)
        )

    # Per-device sensors (dynamic, built from sensor coordinator data)
    sensor_entities = _build_device_sensor_entities(sensor_coord, entry.entry_id, smid)
    entities.extend(sensor_entities)

    async_add_entities(entities)


def _build_device_sensor_entities(
    coord: SolarManagerSensorCoordinator,
    entry_id: str,
    smid: str,
) -> list[SensorEntity]:
    """Build sensor entities from the per-device sensor data returned at startup."""
    entities: list[SensorEntity] = []
    sensor_data = coord.data or []

    for sensor in sensor_data:
        sensor_id = sensor.get("_id") or sensor.get("id", "")
        sensor_name = sensor.get("name") or sensor.get("type", sensor_id)
        sensor_type = sensor.get("type", "").lower()

        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{sensor_id}")},
            name=sensor_name,
            manufacturer="Solar Manager AG",
            model=sensor.get("type", "Device"),
            via_device=(DOMAIN, entry_id),
        )

        # Power sensor — almost all devices have currentPower
        if "currentPower" in sensor or sensor_type in (
            "inverter", "battery", "heatpump", "ev_charger", "smart_plug",
            "water_heater", "consumption_meter", "pv_string",
        ):
            entities.append(
                SolarManagerDevicePowerSensor(
                    coord, sensor_id, "currentPower",
                    SolarManagerSensorDescription(
                        key=f"{sensor_id}_power",
                        name=f"{sensor_name} Power",
                        native_unit_of_measurement=UnitOfPower.WATT,
                        device_class=SensorDeviceClass.POWER,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon="mdi:lightning-bolt",
                    ),
                    device_info,
                )
            )

        # Energy today
        if "energyToday" in sensor:
            entities.append(
                SolarManagerDevicePowerSensor(
                    coord, sensor_id, "energyToday",
                    SolarManagerSensorDescription(
                        key=f"{sensor_id}_energy_today",
                        name=f"{sensor_name} Energy Today",
                        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.TOTAL_INCREASING,
                        icon="mdi:counter",
                    ),
                    device_info,
                )
            )

        # Battery state of charge
        if "SOC" in sensor or "soc" in sensor:
            soc_key = "SOC" if "SOC" in sensor else "soc"
            entities.append(
                SolarManagerDevicePowerSensor(
                    coord, sensor_id, soc_key,
                    SolarManagerSensorDescription(
                        key=f"{sensor_id}_soc",
                        name=f"{sensor_name} State of Charge",
                        native_unit_of_measurement=PERCENTAGE,
                        device_class=SensorDeviceClass.BATTERY,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon="mdi:battery",
                    ),
                    device_info,
                )
            )

        # Water / heat temperature
        if "currentWaterTemp" in sensor:
            entities.append(
                SolarManagerDevicePowerSensor(
                    coord, sensor_id, "currentWaterTemp",
                    SolarManagerSensorDescription(
                        key=f"{sensor_id}_temperature",
                        name=f"{sensor_name} Temperature",
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon="mdi:thermometer",
                    ),
                    device_info,
                )
            )

        # Consumed last 24h
        if "consumedForLast24h" in sensor:
            entities.append(
                SolarManagerDevicePowerSensor(
                    coord, sensor_id, "consumedForLast24h",
                    SolarManagerSensorDescription(
                        key=f"{sensor_id}_consumed_24h",
                        name=f"{sensor_name} Consumed (24h)",
                        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                        device_class=SensorDeviceClass.ENERGY,
                        state_class=SensorStateClass.MEASUREMENT,
                        icon="mdi:chart-bar",
                    ),
                    device_info,
                )
            )

    return entities


# ---------------------------------------------------------------------------
# Base entity
# ---------------------------------------------------------------------------

class SolarManagerBaseEntity(CoordinatorEntity, SensorEntity):
    """Base class for all Solar Manager sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_info = device_info
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info


# ---------------------------------------------------------------------------
# Real-time gateway sensors
# ---------------------------------------------------------------------------

class SolarManagerRealtimeSensor(SolarManagerBaseEntity):
    """Sensor reading values from the gateway real-time stream."""

    def __init__(
        self,
        coordinator: SolarManagerRealtimeCoordinator,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, description, device_info, entry_id)
        self._key = description.key

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_value()
        self.async_write_ha_state()

    def _update_value(self) -> None:
        data: dict = self.coordinator.data or {}

        if self._key == "gridImportPower":
            grid = data.get("currentGridPower", 0) or 0
            self._attr_native_value = max(0, grid)
        elif self._key == "gridExportPower":
            grid = data.get("currentGridPower", 0) or 0
            self._attr_native_value = max(0, -grid)
        elif self._key == "selfConsumptionPower":
            pv = data.get("currentPvGeneration", 0) or 0
            grid_export = max(0, -(data.get("currentGridPower", 0) or 0))
            self._attr_native_value = max(0, pv - grid_export)
        else:
            self._attr_native_value = data.get(self._key)

    @property
    def native_value(self):
        self._update_value()
        return self._attr_native_value


# ---------------------------------------------------------------------------
# Statistics sensors
# ---------------------------------------------------------------------------

class SolarManagerStatisticsSensor(SolarManagerBaseEntity):
    """Sensor reading values from the daily statistics endpoint."""

    def __init__(
        self,
        coordinator: SolarManagerStatisticsCoordinator,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, description, device_info, entry_id)
        self._key = description.key

    @property
    def native_value(self):
        data: dict = self.coordinator.data or {}
        return data.get(self._key)


# ---------------------------------------------------------------------------
# Forecast sensors
# ---------------------------------------------------------------------------

class SolarManagerForecastSensor(SolarManagerBaseEntity):
    """Sensor reading values from the forecast endpoint."""

    def __init__(
        self,
        coordinator: SolarManagerForecastCoordinator,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, description, device_info, entry_id)
        self._key = description.key

    @property
    def native_value(self):
        data: dict = self.coordinator.data or {}
        return data.get(self._key)


# ---------------------------------------------------------------------------
# Tariff sensors
# ---------------------------------------------------------------------------

class SolarManagerTariffSensor(SolarManagerBaseEntity):
    """Sensor reading tariff values."""

    def __init__(
        self,
        coordinator: SolarManagerTariffCoordinator,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, description, device_info, entry_id)
        self._key = description.key

    @property
    def native_value(self):
        data: dict = self.coordinator.data or {}
        return data.get(self._key)


# ---------------------------------------------------------------------------
# Per-device sensors (dynamic)
# ---------------------------------------------------------------------------

class SolarManagerDevicePowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a specific field on a specific device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarManagerSensorCoordinator,
        sensor_id: str,
        field: str,
        description: SolarManagerSensorDescription,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._sensor_id = sensor_id
        self._field = field
        self._device_info = device_info
        self._attr_unique_id = f"{sensor_id}_{field}"

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    def _get_sensor_data(self) -> dict:
        for s in (self.coordinator.data or []):
            sid = s.get("_id") or s.get("id", "")
            if sid == self._sensor_id:
                return s
        return {}

    @property
    def native_value(self):
        return self._get_sensor_data().get(self._field)
