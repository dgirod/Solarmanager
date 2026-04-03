# Solar Manager — Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/dgirod/Solarmanager.svg)](https://github.com/dgirod/Solarmanager/releases)
[![License](https://img.shields.io/github/license/dgirod/Solarmanager.svg)](LICENSE)

Home Assistant integration for the **Solar Manager** smart energy management system (solarmanager.ch). Install via HACS.

---

## Features

- **~40–80 sensors** depending on your installation
- Real-time data updated every **10 seconds**
- Daily energy statistics updated every **5 minutes**
- PV production forecast for today and tomorrow
- Live energy tariff display (static and dynamic)
- Per-device sensors (inverter, battery, heat pump, EV charger, V2X, smart plugs, water heater)
- **Control entities**: set operating modes for battery, inverter, heat pump, EV charger, water heater
- **Smart plug and switch** control
- Full **Energy Dashboard** integration
- German and English translations
- No external Python dependencies

---

## Installation via HACS

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/dgirod/Solarmanager` as category **Integration**.
4. Click **Download** on the Solar Manager card.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and search for **Solar Manager**.

---

## Configuration

You will need:

| Field | Description |
|-------|-------------|
| **Name** | A friendly name for this integration |
| **E-Mail** | Your solarmanager.ch login e-mail |
| **Password** | Your solarmanager.ch password |
| **Smart Manager ID (SMID)** | Found in solarmanager.ch → Settings (format: `SM-XXXXXX`) |

---

## Sensors

### Real-time (updated every 10 s)

| Sensor | Description | Unit |
|--------|-------------|------|
| PV Generation | Current solar production | W |
| Power Consumption | Current total consumption | W |
| Battery Power | Charge (+) / Discharge (−) | W |
| Grid Power | Import (+) / Export (−) | W |
| Grid Import Power | Grid consumption only | W |
| Grid Export Power | Grid feed-in only | W |
| Self Consumption Power | Solar used directly | W |
| Battery State of Charge | Battery level | % |

### Daily Statistics (updated every 5 min)

| Sensor | Description | Unit |
|--------|-------------|------|
| Daily PV Production | Total solar produced today | Wh |
| Daily Consumption | Total energy consumed today | Wh |
| Daily Self Consumption | Solar used directly today | Wh |
| Daily Grid Feed-In | Exported to grid today | Wh |
| Daily Grid Purchase | Imported from grid today | Wh |
| Daily Battery Charged | Battery charged today | Wh |
| Daily Battery Discharged | Battery discharged today | Wh |
| Self Consumption Rate | % of solar used directly | % |
| Autarchy Degree | % of consumption from solar | % |

### Forecast (updated every 30 min)

| Sensor | Description | Unit |
|--------|-------------|------|
| PV Forecast Today | Expected production today | Wh |
| PV Forecast Tomorrow | Expected production tomorrow | Wh |

### Tariffs (updated every 15 min)

| Sensor | Description | Unit |
|--------|-------------|------|
| Energy Tariff Buy | Current purchase price | CHF/kWh |
| Energy Tariff Sell | Current feed-in tariff | CHF/kWh |

### Device-specific (dynamic, updated every 30 s)

Sensors are automatically created for each device registered in your Solar Manager gateway:
- **Inverter**: power, voltage, frequency
- **Battery**: power, voltage, current, temperature, SoC
- **Heat pump**: power, temperature
- **EV charger**: power, session energy, status
- **V2X charger**: power, vehicle SoC
- **Smart plug**: power, energy, switch state
- **Water heater**: temperature, power
- **Consumption meter**: power, energy

---

## Control Entities

### Select (mode control)

| Entity | Options |
|--------|---------|
| Battery Mode | `auto`, `charge`, `discharge`, `idle` |
| Inverter Mode | `auto`, `off`, `manual` |
| Heat Pump Mode | `auto`, `on`, `off`, `boost` |
| EV Charger Mode | `auto`, `fast`, `solar_only`, `off` |
| V2X Mode | `auto`, `charge`, `discharge`, `idle` |
| Water Heater Mode | `auto`, `on`, `off`, `boost` |

### Switches

Smart plugs and switch devices appear as HA switch entities and can be toggled on/off.

---

## Energy Dashboard Setup

After installation, go to **Settings → Dashboards → Energy** and map the sensors:

| Dashboard slot | Sensor |
|----------------|--------|
| Solar production | `sensor.solar_manager_daily_pv_production` |
| Grid consumption | `sensor.solar_manager_daily_grid_purchase` |
| Grid return | `sensor.solar_manager_daily_grid_feed_in` |
| Battery charge | `sensor.solar_manager_daily_battery_charged` |
| Battery discharge | `sensor.solar_manager_daily_battery_discharged` |
| Home consumption | `sensor.solar_manager_daily_consumption` |

---

## Troubleshooting

**"Cannot connect" error during setup**
- Verify your internet connection.
- Check that the solarmanager.ch cloud is reachable.

**"Invalid auth" error**
- Double-check your e-mail address, password, and SMID.
- The SMID typically looks like `SM-123456` — find it in the solarmanager.ch web UI under Settings.

**Missing device sensors**
- Device-specific sensors only appear if devices are registered and active in your Solar Manager gateway.
- Check the HA logs (`Settings → System → Logs`) for details.

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Credits

Inspired by [goir/ha-solarmanager-ch](https://github.com/goir/ha-solarmanager-ch). API: [solar-manager.ch](https://external-web.solar-manager.ch/swagger).
