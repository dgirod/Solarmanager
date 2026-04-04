"""Constants for the Solar Manager integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__name__)

NAME = "Solar Manager"
DOMAIN = "solarmanager"
VERSION = "1.0.6"
ATTRIBUTION = "Data provided by solar-manager.ch"

# Config entry keys
CONF_SMART_MANAGER_ID = "smid"

# API
API_BASE_URL = "https://cloud.solar-manager.ch"

# Update intervals (seconds)
SCAN_INTERVAL_REALTIME = 10
SCAN_INTERVAL_STATISTICS = 300   # 5 min
SCAN_INTERVAL_FORECAST = 1800    # 30 min
SCAN_INTERVAL_TARIFF = 900       # 15 min
SCAN_INTERVAL_SENSORS = 30       # 30 s

# Battery modes
BATTERY_MODES = ["auto", "charge", "discharge", "idle"]

# Inverter modes
INVERTER_MODES = ["auto", "off", "manual"]

# Heat pump modes
HEATPUMP_MODES = ["auto", "on", "off", "boost"]

# EV charger charging modes — maps human-readable HA label → API integer (chargingMode)
# 0=Fast Charge, 1=Solar Only, 2=Solar & Optimized, 3=Do Not Charge, 5=Minimal & Solar
EV_CHARGER_MODE_MAP: dict[str, int] = {
    "Always Charge": 0,
    "Solar Only": 1,
    "Solar & Optimized": 2,
    "Do Not Charge": 3,
    "Constant Current": 4,
    "Minimal & Solar": 5,
    "Min. Charge Quantity": 6,
}
EV_CHARGER_MODES: list[str] = list(EV_CHARGER_MODE_MAP.keys())

# V2X modes
V2X_MODES = ["auto", "charge", "discharge", "idle"]

# Water heater modes
WATER_HEATER_MODES = ["auto", "on", "off", "boost"]
