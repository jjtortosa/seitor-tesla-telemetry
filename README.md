# Tesla Fleet Telemetry Self-Hosted

Self-hosted Tesla Fleet Telemetry server with custom Home Assistant integration for real-time vehicle data streaming.

---

## ⚠️ Difficulty Warning

> **This is an ADVANCED project.** Estimated setup time: **8-12 hours**.

### You SHOULD attempt this if you:
- ✅ Have experience with Docker, Linux, and command line
- ✅ Understand networking (DNS, port forwarding, SSL certificates)
- ✅ Own a server (Proxmox, Synology, VPS, etc.)
- ✅ Have a domain name you control
- ✅ Are comfortable debugging complex systems
- ✅ Want full control and don't mind the effort

### You should NOT attempt this if you:
- ❌ Only install integrations via HACS with one click
- ❌ Have never used SSH or a terminal
- ❌ Don't have your own server infrastructure
- ❌ Expect it to "just work" without troubleshooting

### Easier Alternative

**[Teslemetry.com](https://teslemetry.com)** - $5/month, 30-minute setup, same real-time data. Seriously consider this if you value your time.

### Requirements Summary

| Requirement | Difficulty |
|-------------|------------|
| Tesla Developer account (partner registration) | 🟡 Medium |
| Public domain + Let's Encrypt SSL | 🟡 Medium |
| Server running Docker + Fleet Telemetry | 🔴 High |
| Public port 443 (port forwarding/DDNS) | 🔴 High |
| EC key pair + virtual key pairing | 🔴 High |
| OAuth flow + token management | 🟡 Medium |
| Send telemetry config to vehicle | 🔴 High |
| **MQTT broker in Home Assistant** | 🟢 Easy |

---

## Overview

This project provides a complete solution for streaming Tesla vehicle data to Home Assistant using Tesla's Fleet Telemetry API. Unlike polling-based approaches, this system receives push notifications from your Tesla vehicle with sub-second latency.

### Key Features

- **Real-time streaming**: <1 second latency for location, shift state, speed, and more
- **Self-hosted**: Full control over your data and infrastructure
- **No monthly fees**: Free alternative to Teslemetry service
- **Custom HA integration**: Native Home Assistant integration with device tracker and sensors
- **Battery efficient**: No unnecessary vehicle wake-ups
- **MQTT native**: Uses Home Assistant's built-in MQTT integration (v2.0+)
- **JSON format**: Simple JSON messages, no Protobuf complexity

### Architecture

```
Tesla Vehicle → Fleet Telemetry → MQTT → Home Assistant
                (your server)      ↑      (custom_component)
                                   |
                              Mosquitto
                            (HA add-on)
```

## Components

### 1. Server (`server/`)
Docker-based Fleet Telemetry server with MQTT output.

- **Technologies**: Docker, Tesla Fleet Telemetry, MQTT
- **Requirements**: Public domain with valid SSL, port 443 exposed
- **Resource usage**: 2 CPU cores, 2GB RAM, 10GB disk
- **Data format**: JSON via MQTT topics

### 2. Home Assistant Integration (`ha-integration/`)
Custom component that subscribes to MQTT and creates HA entities.

- **Entities created**: `device_tracker`, sensors, binary_sensors (13 total)
- **Real-time updates**: Location, speed, battery, charging, TPMS, temperature
- **No polling required**: Push-based updates via MQTT
- **Dependency**: Requires MQTT integration configured in HA

### 3. Documentation (`docs/`)
Complete setup guides from infrastructure to automation examples.

## Available Telemetry Fields

| Category | Fields |
|----------|--------|
| **Location** | Location (GPS), VehicleSpeed, Gear |
| **Battery** | Soc, BatteryLevel, EstBatteryRange, ChargeState, DetailedChargeState |
| **Charging** | ChargerVoltage, ChargerCurrent, ChargeLimitSoc |
| **TPMS** | TpmsPressureFl, TpmsPressureFr, TpmsPressureRl, TpmsPressureRr |
| **Climate** | InsideTemp, OutsideTemp |
| **Security** | DoorState, SentryMode, Locked |
| **Other** | Odometer |

## Quick Start

### Prerequisites

- Docker host (Proxmox VM, dedicated server, etc.)
- Domain name with DNS control
- Tesla account with vehicle (firmware 2024.26+)
- Home Assistant instance with **MQTT configured** (Mosquitto add-on recommended)

### Setup Steps

1. **Infrastructure Setup**
   - Create VM/container for fleet-telemetry
   - Configure DNS: `tesla-telemetry.yourdomain.com` (direct A record, NOT proxied)
   - Generate Let's Encrypt SSL certificate

2. **Tesla Developer Setup**
   - Create application on [developer.tesla.com](https://developer.tesla.com)
   - Generate EC key pair
   - Register partner account
   - Complete OAuth authorization
   - Pair virtual key with vehicle

3. **Server Deployment**
   - Deploy Fleet Telemetry with **MQTT output**
   - Configure to publish to your Mosquitto broker
   - Test vehicle connection

4. **HA Integration**
   - Install Mosquitto add-on in Home Assistant
   - Configure MQTT integration
   - Copy `custom_components/tesla_telemetry_local/` to HA
   - Add integration via UI: **Settings → Devices & Services → Add Integration**
   - Search for "Tesla Fleet Telemetry Local"

## Configuration

### Fleet Telemetry Server Config (MQTT)

```json
{
  "host": "0.0.0.0",
  "port": 443,
  "log_level": "info",
  "mqtt": {
    "broker": "192.168.5.201:1883",
    "client_id": "fleet-telemetry",
    "username": "mqtt_user",
    "password": "mqtt_password",
    "topic_base": "tesla",
    "qos": 1,
    "retained": true
  },
  "records": {
    "V": ["mqtt"],
    "alerts": ["mqtt"],
    "errors": ["mqtt"]
  },
  "reliable_ack_sources": {
    "V": "mqtt"
  },
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  }
}
```

### Home Assistant Configuration

**Via UI (recommended):**
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "Tesla Fleet Telemetry Local"
3. Enter:
   - **MQTT Topic Base**: `tesla` (must match server config)
   - **Vehicle VIN**: Your 17-character VIN
   - **Vehicle Name**: Friendly name (e.g., "MelanY")

**Note:** MQTT broker configuration is handled by HA's MQTT integration.

### MQTT Topic Structure

Fleet Telemetry publishes to these topics:

```
tesla/<VIN>/v/VehicleSpeed      → {"value": 65}
tesla/<VIN>/v/BatteryLevel      → {"value": 78}
tesla/<VIN>/v/Location          → {"latitude": 41.38, "longitude": 2.17}
tesla/<VIN>/v/ChargeState       → {"value": "Charging"}
tesla/<VIN>/connectivity        → {"Status": "connected"}
tesla/<VIN>/alerts/#            → Alert messages
```

### Telemetry Config (send to vehicle)

```json
{
  "vins": ["YOUR_VIN"],
  "config": {
    "hostname": "tesla-telemetry.yourdomain.com",
    "port": 443,
    "ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
    "fields": {
      "Location": { "interval_seconds": 1 },
      "VehicleSpeed": { "interval_seconds": 1 },
      "BatteryLevel": { "interval_seconds": 10 },
      "InsideTemp": { "interval_seconds": 30 },
      "TpmsPressureFl": { "interval_seconds": 60 }
    },
    "alert_types": ["service"]
  }
}
```

## Automation Examples

### Open Garage on Arrival

```yaml
- id: 'tesla_garage_auto'
  alias: Tesla automatic garage
  triggers:
    - entity_id: device_tracker.tesla_YOUR_VIN
      zone: zone.home
      event: enter
      trigger: zone
  conditions:
    - condition: time
      after: '07:00:00'
      before: '23:00:00'
  actions:
    - action: cover.open_cover
      target:
        entity_id: cover.garage_door
    - action: notify.mobile_app
      data:
        title: "Tesla"
        message: "Arriving home - garage opened"
```

### Low Battery Notification

```yaml
- id: 'tesla_low_battery'
  alias: Tesla low battery alert
  triggers:
    - entity_id: sensor.tesla_battery
      below: 20
      trigger: numeric_state
  actions:
    - action: notify.mobile_app
      data:
        title: "Tesla Battery Low"
        message: "Battery at {{ states('sensor.tesla_battery') }}%"
```

## Cost Comparison

| Solution | Monthly Cost | Latency | Setup Time | Control |
|----------|--------------|---------|------------|---------|
| **This project** | $0 (domain ~$1/mo) | <1s | 8-12h | Full |
| Teslemetry | $5/month | <1s | 30min | Limited |
| Tesla Fleet API polling | $0 | 2-15min | 2h | Full |

## Troubleshooting

### Common Issues

1. **Vehicle not sending data**
   - Check firmware version (2024.26+ required)
   - Verify virtual key is paired
   - Check telemetry config was sent successfully

2. **MQTT connection errors**
   - Verify Mosquitto add-on is running
   - Check MQTT integration is configured in HA
   - Verify topic_base matches server config

3. **Integration shows "MQTT not configured"**
   - Install Mosquitto broker add-on
   - Configure MQTT integration in HA
   - Restart Home Assistant

4. **device_tracker not updating**
   - Check Location field is configured in telemetry
   - Verify MQTT messages arriving: `mosquitto_sub -t "tesla/#" -v`
   - Check HA logs for errors

5. **Certificate errors**
   - Must use Let's Encrypt or Tesla-trusted CA
   - Domain must NOT be behind Cloudflare proxy

## Migration from v1.x (Kafka)

If upgrading from the Kafka-based version:

1. Remove old integration from HA
2. Install Mosquitto add-on (if not already)
3. Update Fleet Telemetry server config to use MQTT instead of Kafka
4. Copy new integration files
5. Add integration via UI

**Breaking changes in v2.0:**
- No longer requires `kafka-python` dependency
- Configuration via UI instead of YAML
- Requires MQTT integration in Home Assistant

## Support

This is a personal project for home automation. While documented thoroughly:

- ⚠️ Advanced technical knowledge required
- ⚠️ No official support or guarantees
- ⚠️ You're responsible for your own infrastructure
- ✅ All documentation and code provided as-is

## License

MIT License - see [LICENSE](LICENSE) file

## Credits

- Tesla for Fleet Telemetry API
- Home Assistant community
- Based on [tesla/fleet-telemetry](https://github.com/teslamotors/fleet-telemetry)

---

**Status**: ✅ v2.0.0 - MQTT Edition

- ✅ Migrated from Kafka to MQTT (simpler setup)
- ✅ Uses Home Assistant's native MQTT integration
- ✅ Config Flow UI (no YAML required)
- ✅ Real-world tested and working
- ✅ JSON format (easier debugging)
- ✅ device_tracker with zone triggers
- ✅ 13 entities per vehicle
