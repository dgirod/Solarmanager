"""Constants for the Solar Manager integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__name__)

NAME = "Solar Manager"
DOMAIN = "solarmanager"
VERSION = "1.0.0"
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

# EV charger modes
EV_CHARGER_MODES = ["auto", "fast", "solar_only", "off"]

# V2X modes
V2X_MODES = ["auto", "charge", "discharge", "idle"]

# Water heater modes
WATER_HEATER_MODES = ["auto", "on", "off", "boost"]
