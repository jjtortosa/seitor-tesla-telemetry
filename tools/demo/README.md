# Tesla Fleet Telemetry Demo

Live demo environment for showcasing the Tesla Fleet Telemetry integration.

🌐 **Live Demo**: https://demo.seitor.com

## What's Included

- **Mock Telemetry Generator**: Simulates realistic Tesla vehicle data
- **Pre-configured Integration**: Ready-to-use Home Assistant setup
- **Multiple Scenarios**: Parked, driving, charging, arriving home

## Quick Start (Local Demo)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git
cd seitor-tesla-telemetry

# Start the demo stack
docker compose -f docker-compose.demo.yml up -d

# Access Home Assistant
open http://localhost:8123
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install paho-mqtt

# Run mock telemetry
python tools/demo/mock_telemetry.py \
  --mqtt-host YOUR_MQTT_HOST \
  --scenario driving \
  --continuous
```

## Mock Telemetry Generator

### Usage

```bash
python mock_telemetry.py [OPTIONS]

Options:
  -s, --scenario    Simulation scenario (parked, driving, charging, arriving_home, trip)
  -d, --duration    Duration in seconds (default: 60)
  -i, --interval    Update interval in seconds (default: 5)
  --mqtt-host       MQTT broker host (default: localhost)
  --mqtt-port       MQTT broker port (default: 1883)
  --vin            Vehicle VIN (default: DEMO0TESLA0VIN00)
  -c, --continuous  Run continuously
```

### Scenarios

| Scenario | Description |
|----------|-------------|
| `parked` | Vehicle stationary, minimal changes |
| `driving` | City driving with speed/location updates |
| `charging` | Charging session with battery increase |
| `arriving_home` | Approaching home zone (triggers automations) |
| `trip` | Complete journey: leave → drive → arrive |

### Examples

```bash
# Simulate parked vehicle for 5 minutes
python mock_telemetry.py --scenario parked --duration 300

# Simulate driving continuously
python mock_telemetry.py --scenario driving --continuous

# Simulate charging session
python mock_telemetry.py --scenario charging --duration 600

# Simulate arriving home (for testing zone automations)
python mock_telemetry.py --scenario arriving_home
```

## Demo Vehicle Data

The mock generator simulates:

| Field | Sample Value | Update Rate |
|-------|--------------|-------------|
| Location | Barcelona area | Every 5s |
| Speed | 0-120 km/h | Every 5s |
| Battery | 10-100% | Every 5s |
| Range | ~350 km | Every 5s |
| Inside Temp | 18-25°C | Every 30s |
| Outside Temp | 10-30°C | Every 30s |
| Tire Pressure | 2.7-3.0 bar | Every 60s |

## Public Demo Setup

See [DEMO_SETUP.md](DEMO_SETUP.md) for complete instructions on:

- DNS configuration (demo.seitor.com)
- Nginx Proxy Manager / Cloudflare Tunnel setup
- HA Test configuration
- Security considerations

## Files

```
tools/demo/
├── README.md                    # This file
├── DEMO_SETUP.md               # Public demo setup guide
├── cloudflare_tunnel_setup.md  # Cloudflare Tunnel alternative
├── mock_telemetry.py           # Mock data generator
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image for mock generator
└── setup_demo.sh              # Automated setup script
```

## Integration with Home Assistant

After starting the mock generator:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Tesla Fleet Telemetry Local**
4. Configure:
   - MQTT Topic Base: `tesla`
   - Vehicle VIN: `DEMO0TESLA0VIN00`
   - Vehicle Name: `Demo Tesla`

## Customization

### Change Demo Vehicle Location

Edit `mock_telemetry.py` and modify the `route_points` in `_scenario_driving()`:

```python
route_points = [
    (YOUR_LAT_1, YOUR_LON_1),
    (YOUR_LAT_2, YOUR_LON_2),
    # Add more points...
]
```

### Change Demo VIN

```bash
python mock_telemetry.py --vin "YOUR_CUSTOM_VIN"
```

## Troubleshooting

### No data in Home Assistant

1. Check MQTT connection: `mosquitto_sub -t "tesla/#" -v`
2. Verify mock script is running: `ps aux | grep mock_telemetry`
3. Check HA logs for integration errors

### Demo not accessible

1. Check Cloudflare Tunnel: `cloudflared tunnel info`
2. Check HA is running: `curl http://localhost:8123`
3. Verify DNS: `nslookup demo.seitor.com`

## License

MIT - See main repository LICENSE file.
