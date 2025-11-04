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

### Architecture

```
Tesla Vehicle → Fleet Telemetry → Kafka → HA Integration → Home Assistant
                (Proxmox CT)              (custom_component)
```

## Components

### 1. Server (`server/`)
Docker-based Fleet Telemetry server with Kafka message queue. Deployed on Proxmox LXC container.

- **Technologies**: Docker, Kafka, Tesla Fleet Telemetry, Nginx
- **Requirements**: Public domain (tesla-telemetry.seitor.com), SSL certificate
- **Resource usage**: 2 CPU cores, 4GB RAM, 20GB disk

### 2. Home Assistant Integration (`ha-integration/`)
Custom component that consumes Kafka messages and creates HA entities.

- **Entities created**: device_tracker, sensors, binary_sensors
- **Real-time updates**: Location, shift state, speed, charging status
- **No polling required**: Push-based updates from Kafka

### 3. Documentation (`docs/`)
Complete setup guides from infrastructure to automation examples.

## Quick Start

### Prerequisites

- Proxmox server (or any Docker host)
- Domain name with DNS control (e.g., seitor.com)
- Tesla account with vehicle
- Home Assistant instance

### Setup Steps

1. **Infrastructure Setup** (1-2 hours)
   - Create Proxmox LXC container
   - Configure DNS: tesla-telemetry.seitor.com
   - Generate SSL certificates

2. **Tesla Developer Setup** (2-3 hours)
   - Create application on developer.tesla.com
   - Generate EC keys
   - Configure virtual key pairing

3. **Server Deployment** (3-4 hours)
   - Deploy Fleet Telemetry + Kafka stack
   - Validate certificate
   - Test vehicle connection

4. **HA Integration** (1-2 hours)
   - Install custom component
   - Configure Kafka connection
   - Test entity updates

**Total estimated time**: 7-11 hours (first setup)

## Documentation

- [01 - Project Overview](docs/01_overview.md)
- [02 - Infrastructure Setup](docs/02_infrastructure_setup.md)
- [03 - Tesla Developer Setup](docs/03_tesla_developer_setup.md)
- [04 - Server Deployment](docs/04_server_deployment.md)
- [05 - Home Assistant Integration](docs/05_ha_integration.md)
- [06 - Troubleshooting](docs/06_troubleshooting.md)

## Cost Comparison

| Solution | Monthly Cost | Latency | Setup Time | Control |
|----------|--------------|---------|------------|---------|
| **This project** | $0 (domain ~$1/mo) | <1s | 7-11h | Full |
| Teslemetry | $5/month | <1s | 30min | Limited |
| Tesla Fleet API polling | $0 | 2-15min | 2h | Full |

## Support

This is a personal project for home automation. While I've documented everything thoroughly, please note:

- ⚠️ Advanced technical knowledge required (Docker, Kafka, Protobuf)
- ⚠️ No official support or guarantees
- ⚠️ You're responsible for your own infrastructure
- ✅ All documentation and code provided as-is

## License

MIT License - see [LICENSE](LICENSE) file

## Credits

- Tesla for Fleet Telemetry API
- Home Assistant community
- Based on [tesla/fleet-telemetry](https://github.com/teslamotors/fleet-telemetry)

## Author

Built by [@seitor](https://github.com/seitor) for personal use at ha.seitor.com

---

**Status**: ✅ v0.1.0 - Core implementation complete

- ✅ Documentation (6 guides, ~20k words)
- ✅ Server infrastructure (Docker Compose stack)
- ✅ Home Assistant integration (full custom component)
- ⏳ Protobuf schema (placeholder, needs compilation)
- ⏳ Real-world testing pending
