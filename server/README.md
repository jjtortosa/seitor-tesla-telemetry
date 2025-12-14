# Fleet Telemetry Server

Docker-based Tesla Fleet Telemetry server with MQTT output.

## Architecture

```
Tesla Vehicle → Fleet Telemetry Server → MQTT Broker → Home Assistant
               (this server, port 443)   (Mosquitto)   (integration)
```

## Quick Start

### 1. Run Interactive Setup

```bash
./setup.sh
```

This will guide you through:
- Domain configuration
- MQTT broker settings
- Tesla API key generation
- All configuration file creation

### 2. Add SSL Certificates

Copy your certificates to `certs/`:

```bash
certs/
├── fullchain.pem   # Certificate + chain
└── privkey.pem     # Private key
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Verify

```bash
docker compose ps
docker compose logs -f fleet-telemetry
```

---

## Manual Setup (Alternative)

If you prefer manual configuration:

### 1. Copy Configuration

```bash
cp .env.example .env
cp config.json.example config.json
# Edit both files with your settings
```

### 2. Configure MQTT

Edit `config.json` and set your MQTT broker:

```json
{
  "mqtt": {
    "broker": "192.168.5.201:1883",
    "client_id": "fleet-telemetry",
    "username": "your_mqtt_user",
    "password": "your_mqtt_password",
    "topic_base": "tesla",
    "qos": 1,
    "retained": true
  }
}
```

### 3. Generate Keys

```bash
./scripts/generate_keys.sh
```

### 4. Prepare SSL Certificates

```bash
mkdir -p certs
# Copy your certificates:
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

### 5. Start Services

```bash
docker compose up -d
```

## Directory Structure

```
server/
├── docker-compose.yml       # Docker services definition
├── config.json             # Fleet Telemetry configuration (create from .example)
├── config.json.example     # Configuration template
├── .env                    # Environment variables (not in git)
├── certs/                  # SSL certificates
│   ├── fullchain.pem
│   └── privkey.pem
├── keys/                   # Tesla API keys (not in git)
│   ├── private_key.pem
│   ├── public_key.pem
│   └── com.tesla.3p.public-key.pem
├── logs/                   # Fleet Telemetry logs
├── scripts/                # Utility scripts
│   ├── generate_keys.sh
│   ├── validate_cert.sh
│   └── health_check.sh
└── README.md               # This file
```

## Services

### fleet-telemetry
- **Port**: 443 (HTTPS for Tesla vehicles)
- **Port**: 8443 (Metrics/health endpoint)
- **Purpose**: Receives telemetry data from Tesla vehicles, publishes to MQTT
- **Healthcheck**: `curl -k https://localhost:443/health`

## MQTT Topic Structure

Fleet Telemetry publishes to these topics:

```
tesla/<VIN>/v/<field_name>     # Telemetry metrics
tesla/<VIN>/connectivity       # Vehicle connection status
tesla/<VIN>/alerts/<name>      # Vehicle alerts
tesla/<VIN>/errors/<name>      # Error messages
```

### Example Messages

```bash
# Battery level
tesla/LRWYGCFS3RC210528/v/BatteryLevel → {"value": 72}

# Location
tesla/LRWYGCFS3RC210528/v/Location → {"latitude": 41.38, "longitude": 2.17}

# Speed
tesla/LRWYGCFS3RC210528/v/VehicleSpeed → {"value": 65}

# Connectivity
tesla/LRWYGCFS3RC210528/connectivity → {"status": "online"}
```

## Useful Commands

### Start/Stop

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart
docker compose restart fleet-telemetry

# View logs
docker compose logs -f fleet-telemetry
```

### Debugging

```bash
# Check fleet-telemetry health
curl -k https://localhost:443/health

# Check metrics
curl http://localhost:8443/metrics

# Monitor MQTT messages (from HA or MQTT broker)
mosquitto_sub -h 192.168.5.201 -u mqtt_user -P mqtt_pass -t "tesla/#" -v

# Check container status
docker compose ps
```

### Maintenance

```bash
# Update images
docker compose pull
docker compose up -d

# View resource usage
docker stats fleet-telemetry
```

## Configuration

### config.json

| Field | Description |
|-------|-------------|
| `host` | Bind address (0.0.0.0) |
| `port` | HTTPS port (443) |
| `tls.server_cert` | Path to SSL certificate |
| `tls.server_key` | Path to SSL private key |
| `mqtt.broker` | MQTT broker host:port |
| `mqtt.topic_base` | Base topic for messages |
| `mqtt.qos` | Quality of Service (0, 1, 2) |
| `mqtt.retained` | Retain messages on broker |
| `records` | Which record types to send to mqtt |

### .env

| Variable | Description |
|----------|-------------|
| `TELEMETRY_DOMAIN` | Your public domain |
| `MQTT_HOST` | MQTT broker IP |
| `MQTT_PORT` | MQTT broker port (1883) |
| `MQTT_USERNAME` | MQTT authentication user |
| `MQTT_PASSWORD` | MQTT authentication password |
| `MQTT_TOPIC_BASE` | Base topic (default: tesla) |
| `LOG_LEVEL` | Logging level |

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs fleet-telemetry

# Common issues:
# - Invalid config.json syntax
# - Missing certificates
# - Port 443 already in use
```

### Certificate errors

```bash
# Validate certificate
./scripts/validate_cert.sh tesla-telemetry.seitor.com

# Check certificate dates
openssl x509 -in certs/fullchain.pem -noout -dates
```

### MQTT not receiving messages

```bash
# Check fleet-telemetry logs
docker compose logs fleet-telemetry | grep -i mqtt

# Verify MQTT broker is reachable
nc -zv 192.168.5.201 1883

# Test MQTT publish manually
mosquitto_pub -h 192.168.5.201 -u user -P pass -t "test" -m "hello"
```

### Vehicle not connecting

1. Check virtual key is paired: Tesla app → Vehicle → Keys
2. Verify telemetry config sent to vehicle
3. Check fleet-telemetry logs for connection attempts:
   ```bash
   docker compose logs -f fleet-telemetry | grep -i vehicle
   ```
4. Ensure port 443 is accessible from internet:
   ```bash
   # From outside network
   nc -zv tesla-telemetry.seitor.com 443
   ```

## Next Steps

1. Configure virtual key pairing (see main docs)
2. Send telemetry config to vehicle
3. Install Home Assistant integration
4. Create automations

---

For detailed setup instructions, see:
- [02 - Infrastructure Setup](../docs/02_infrastructure_setup.md)
- [03 - Tesla Developer Setup](../docs/03_tesla_developer_setup.md)
- [04 - Server Deployment](../docs/04_server_deployment.md)
