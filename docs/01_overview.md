# Project Overview

## What is This Project?

A complete self-hosted solution for streaming real-time Tesla vehicle data to Home Assistant using Tesla's Fleet Telemetry API. This eliminates the need for polling and provides sub-second latency for location updates, driving state, and other vehicle data.

## Architecture Diagram

```
┌─────────────────┐
│  Tesla Vehicle  │
│   (MelanY)      │
└────────┬────────┘
         │ Fleet Telemetry Protocol
         │ (Push, WebSocket + mTLS)
         ▼
┌─────────────────────────────────────┐
│    tesla-telemetry.seitor.com       │
│  ┌───────────────────────────────┐  │
│  │   Fleet Telemetry Server      │  │
│  │   (Docker Container)          │  │
│  │   - Receives vehicle data     │  │
│  │   - Validates mTLS            │  │
│  │   - Parses Protobuf           │  │
│  └────────────┬──────────────────┘  │
│               │                      │
│               ▼                      │
│  ┌───────────────────────────────┐  │
│  │   Kafka Message Queue         │  │
│  │   Topics:                     │  │
│  │   - tesla_V (vehicle data)    │  │
│  │   - tesla_connectivity        │  │
│  │   - tesla_alerts              │  │
│  └────────────┬──────────────────┘  │
│               │                      │
│     Proxmox LXC Container           │
└───────────────┼─────────────────────┘
                │ Kafka Protocol
                │ (Internal network)
                ▼
┌─────────────────────────────────────┐
│    Home Assistant (ha.seitor.com)   │
│  ┌───────────────────────────────┐  │
│  │  tesla_telemetry_local        │  │
│  │  (Custom Integration)         │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Kafka Consumer         │  │  │
│  │  │  - Subscribes to topics │  │  │
│  │  │  - Parses Protobuf      │  │  │
│  │  │  - Creates HA entities  │  │  │
│  │  └──────────┬──────────────┘  │  │
│  │             │                 │  │
│  │             ▼                 │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Entity Manager         │  │  │
│  │  │  - device_tracker       │  │  │
│  │  │  - sensors              │  │  │
│  │  │  - binary_sensors       │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│         Automations                 │
│  - Garage door (zone entry)         │
│  - Notifications (driving state)    │
│  - Charging optimizations           │
└─────────────────────────────────────┘
```

## Data Flow

### 1. Vehicle → Fleet Telemetry Server

**Protocol**: WebSocket with mutual TLS (mTLS)
**Frequency**: Configured per field (e.g., location every 5s, shift state every 1s)
**Format**: Protocol Buffers (Protobuf)

When configured, the Tesla vehicle establishes a persistent WebSocket connection to the Fleet Telemetry server. The vehicle sends binary Protobuf messages containing the requested data fields.

**Example message fields**:
- `Location` (lat, lon, heading)
- `ShiftState` (P, D, R, N)
- `Speed` (km/h)
- `Soc` (battery %)
- `ChargingState` (charging, complete, disconnected)

### 2. Fleet Telemetry Server → Kafka

The server validates the mTLS certificate, parses the Protobuf message, and publishes it to Kafka topics:

- **`tesla_V`**: Vehicle data (location, speed, etc.)
- **`tesla_connectivity`**: Connection events (connected, disconnected)
- **`tesla_alerts`**: Vehicle alerts and errors

### 3. Kafka → Home Assistant Integration

The custom HA integration subscribes to Kafka topics as a consumer. When messages arrive:

1. **Parse Protobuf**: Decode binary message using `vehicle_data.proto`
2. **Extract fields**: Location, shift state, speed, etc.
3. **Update entities**:
   - `device_tracker.melan_y_location` → GPS coordinates
   - `sensor.melan_y_shift_state` → Current gear
   - `sensor.melan_y_speed` → Current speed
   - `binary_sensor.melan_y_driving` → Driving state
4. **Trigger automations**: Zone-based (garage door), state-based (notifications)

### 4. Home Assistant → Automations

With real-time entity updates (<1s latency), automations become reliable:

```yaml
# Garage door automation (WORKS with streaming!)
automation:
  - trigger:
      - platform: zone
        entity_id: device_tracker.melan_y_location
        zone: zone.home
        event: enter
    action:
      - service: cover.open_cover
        target:
          entity_id: cover.garage_door
```

**With polling (old system)**: 5-15 minute latency → misses short trips
**With streaming (this system)**: <1 second latency → always triggers

## Components Deep Dive

### Fleet Telemetry Server

**Technology**: Tesla's official `tesla/fleet-telemetry` Docker image

**Responsibilities**:
- Accept WebSocket connections from Tesla vehicles
- Validate client certificates (mTLS)
- Parse Protobuf messages
- Forward to message queue (Kafka)
- Expose metrics for monitoring

**Resource Requirements**:
- CPU: 2 cores (mostly idle, spikes during message processing)
- RAM: 2-4GB (depends on message buffer size)
- Disk: 10GB (logs + Kafka retention)
- Network: Publicly accessible HTTPS endpoint

### Kafka Message Queue

**Technology**: Confluent Kafka (Docker)

**Responsibilities**:
- Reliable message delivery (vehicle → HA)
- Buffer messages during HA downtime (up to configured retention)
- Enable multiple consumers (future: dashboards, mobile apps)
- Persistence for replay/debugging

**Configuration**:
- Topics: `tesla_V`, `tesla_connectivity`, `tesla_alerts`
- Retention: 7 days (configurable)
- Replication: 1 (single broker for home use)

### Home Assistant Integration

**Technology**: Python custom component

**Files**:
- `__init__.py`: Integration setup, Kafka consumer lifecycle
- `device_tracker.py`: Location entity
- `sensor.py`: Speed, shift state, battery, charging sensors
- `binary_sensor.py`: Driving, charging, connected states
- `kafka_consumer.py`: Kafka client, message parsing
- `vehicle_data_pb2.py`: Compiled Protobuf schema

**Entities Created**:

| Entity ID | Type | Description | Update Frequency |
|-----------|------|-------------|------------------|
| `device_tracker.melan_y_location` | Device Tracker | GPS location | 5 seconds |
| `sensor.melan_y_shift_state` | Sensor | Current gear (P/D/R/N) | 1 second |
| `sensor.melan_y_speed` | Sensor | Speed (km/h) | 1 second |
| `sensor.melan_y_battery` | Sensor | Battery level (%) | 60 seconds |
| `sensor.melan_y_range` | Sensor | Remaining range (km) | 60 seconds |
| `binary_sensor.melan_y_driving` | Binary Sensor | Driving state | 1 second |
| `binary_sensor.melan_y_charging` | Binary Sensor | Charging state | 30 seconds |
| `binary_sensor.melan_y_connected` | Binary Sensor | Vehicle connectivity | Real-time |

## Why Self-Host Instead of Teslemetry?

### Advantages

| Feature | Self-Hosted | Teslemetry ($5/mo) |
|---------|-------------|---------------------|
| **Cost** | ~$1/mo (domain) | $5/mo |
| **Data control** | Full | Limited |
| **Customization** | Unlimited | Limited |
| **Privacy** | Local network | Third-party |
| **Learning** | High | Low |
| **Reliability** | Your responsibility | SLA guaranteed |

### Disadvantages

| Feature | Self-Hosted | Teslemetry |
|---------|-------------|------------|
| **Setup time** | 7-11 hours | 30 minutes |
| **Technical skills** | Advanced | Basic |
| **Maintenance** | Manual | Managed |
| **Support** | Community | Official |
| **Downtime risk** | Possible | Minimal |

### When to Choose Self-Hosted?

✅ You enjoy learning new technologies (Docker, Kafka, Protobuf)
✅ You have a home server (Proxmox, NAS, VPS)
✅ You value data privacy and control
✅ You want to customize beyond standard features
✅ You're comfortable troubleshooting technical issues

### When to Choose Teslemetry?

✅ You want it working in 30 minutes
✅ You prefer managed services over self-hosting
✅ $5/month is acceptable
✅ You want official support
✅ You don't have time for maintenance

## Technical Requirements

### Knowledge Requirements

**Must have**:
- Docker & Docker Compose
- Basic Linux command line
- Understanding of networking (DNS, ports, firewall)
- Git version control

**Should have**:
- Proxmox or LXC containers
- Reverse proxy concepts (Nginx, Traefik)
- SSL/TLS certificates (Let's Encrypt)

**Nice to have**:
- Kafka basics
- Protocol Buffers
- Python development
- Home Assistant custom components

### Infrastructure Requirements

**Mandatory**:
- Server/host for Docker (Proxmox CT, VPS, NAS with Docker)
- Domain name (seitor.com) with DNS control
- Public IP address or DDNS
- SSL certificate (Let's Encrypt works)

**Recommended**:
- Proxmox for LXC isolation
- Static IP or reliable DDNS
- Firewall with port forwarding (443)
- Backup solution

### Time Commitment

**Initial setup**: 7-11 hours spread over 1-2 days
**Ongoing maintenance**: 1-2 hours/month
- Certificate renewal: Automated (certbot)
- Docker updates: Monthly
- Monitoring logs: Weekly
- Troubleshooting: As needed

## Success Criteria

After completing this project, you should have:

✅ Fleet Telemetry server running on Proxmox
✅ Tesla vehicle streaming data via HTTPS
✅ Kafka receiving and buffering messages
✅ Home Assistant integration installed
✅ Real-time location updates (<1s latency)
✅ Garage door automation working reliably
✅ Monitoring and health checks in place
✅ Documentation for future troubleshooting

## Next Steps

1. Read [02 - Infrastructure Setup](02_infrastructure_setup.md) to prepare your Proxmox environment
2. Follow [03 - Tesla Developer Setup](03_tesla_developer_setup.md) to configure your Tesla application
3. Deploy the server using [04 - Server Deployment](04_server_deployment.md)
4. Install the HA integration via [05 - Home Assistant Integration](05_ha_integration.md)
5. Refer to [06 - Troubleshooting](06_troubleshooting.md) if you encounter issues

---

**Ready to start?** Proceed to [Infrastructure Setup](02_infrastructure_setup.md) →
