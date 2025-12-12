# Tesla Fleet Telemetry Self-Hosted

Self-hosted Tesla Fleet Telemetry server with custom Home Assistant integration for real-time vehicle data streaming.

## Overview

This project provides a complete solution for streaming Tesla vehicle data to Home Assistant using Tesla's Fleet Telemetry API. Unlike polling-based approaches, this system receives push notifications from your Tesla vehicle with sub-second latency.

### Key Features

- **Real-time streaming**: <1 second latency for location, shift state, speed, and more
- **Self-hosted**: Full control over your data and infrastructure
- **No monthly fees**: Free alternative to Teslemetry service
- **Custom HA integration**: Native Home Assistant integration with device tracker and sensors
- **Battery efficient**: No unnecessary vehicle wake-ups
- **JSON format**: Uses `transmit_decoded_records: true` for easy debugging

### Architecture

```
Tesla Vehicle → Fleet Telemetry → Kafka → HA Integration → Home Assistant
                (Proxmox VM)              (custom_component)
```

## Components

### 1. Server (`server/`)
Docker-based Fleet Telemetry server with Kafka message queue.

- **Technologies**: Docker, Kafka, Tesla Fleet Telemetry
- **Requirements**: Public domain with valid SSL, port 443 exposed
- **Resource usage**: 2 CPU cores, 4GB RAM, 20GB disk
- **Data format**: JSON (not Protobuf) via `transmit_decoded_records: true`

### 2. Home Assistant Integration (`ha-integration/`)
Custom component that consumes Kafka messages and creates HA entities.

- **Entities created**: `device_tracker`, sensors, binary_sensors
- **Real-time updates**: Location, speed, battery, charging, TPMS, temperature
- **No polling required**: Push-based updates from Kafka
- **JSON parsing**: Simplified parsing without Protobuf dependency

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
- Home Assistant instance

### Setup Steps

1. **Infrastructure Setup**
   - Create VM/container for fleet-telemetry + Kafka
   - Configure DNS: `tesla-telemetry.yourdomain.com` (direct A record, NOT proxied)
   - Generate Let's Encrypt SSL certificate

2. **Tesla Developer Setup**
   - Create application on [developer.tesla.com](https://developer.tesla.com)
   - Generate EC key pair
   - Register partner account
   - Complete OAuth authorization
   - Pair virtual key with vehicle

3. **Server Deployment**
   - Deploy Fleet Telemetry + Kafka stack
   - Configure `transmit_decoded_records: true` for JSON output
   - Test vehicle connection

4. **HA Integration**
   - Copy `custom_components/tesla_telemetry_local/` to HA
   - Configure in `configuration.yaml`
   - Restart Home Assistant

## Configuration

### Fleet Telemetry Server Config

```json
{
  "host": "0.0.0.0",
  "port": 443,
  "log_level": "info",
  "transmit_decoded_records": true,
  "kafka": {
    "bootstrap_servers": ["localhost:9092"],
    "topic": "tesla_telemetry_V"
  }
}
```

### Home Assistant Configuration

```yaml
tesla_telemetry_local:
  kafka_broker: "192.168.5.204:29092"
  kafka_topic: "tesla_telemetry_V"
  vehicle_vin: "YOUR_VIN_HERE"
  vehicle_name: "MelanY"
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

2. **Kafka connection errors**
   - Verify Kafka is accessible from HA network
   - Check firewall rules for port 29092

3. **device_tracker not updating**
   - Integration uses `device_tracker.see` service
   - Check HA logs for "Tesla device_tracker" messages

4. **Certificate errors**
   - Must use Let's Encrypt or Tesla-trusted CA
   - Domain must NOT be behind Cloudflare proxy

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

**Status**: ✅ v1.0.0 - Production ready

- ✅ Real-world tested and working
- ✅ JSON format (easier debugging than Protobuf)
- ✅ device_tracker with zone triggers
- ✅ 17 telemetry fields supported
- ✅ Automation examples included
