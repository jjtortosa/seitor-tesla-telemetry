# Migration Guide: Kafka to MQTT

This guide documents the production migration from Kafka to MQTT for Fleet Telemetry.

## Pre-Migration Checklist

- [ ] Backup current configuration files
- [ ] Verify MQTT broker (Mosquitto) is running on HA Real
- [ ] Verify HA integration v2.0.0 (MQTT) is installed
- [ ] Test MQTT connectivity from Fleet Telemetry VM
- [ ] Have rollback procedure ready

## Current Architecture (Kafka)

```
Tesla Vehicle → Fleet Telemetry → Kafka → HA Integration
               (192.168.5.204)   (29092)  (192.168.5.201)
```

## Target Architecture (MQTT)

```
Tesla Vehicle → Fleet Telemetry → MQTT Broker → HA Integration
               (192.168.5.204)   (192.168.5.201:1883)
```

---

## Migration Steps

### Step 1: Backup Current Configuration

```bash
# SSH to Fleet Telemetry VM
ssh root@192.168.5.204

# Create backup directory
mkdir -p /opt/seitor-tesla-telemetry/backup-kafka
cd /opt/seitor-tesla-telemetry

# Backup current files
cp config.json backup-kafka/
cp docker-compose.yml backup-kafka/
cp .env backup-kafka/ 2>/dev/null || true

# Save current container state
docker compose ps > backup-kafka/docker-state.txt
echo "Backup created at $(date)" > backup-kafka/backup-info.txt
```

### Step 2: Verify MQTT Broker

```bash
# From Fleet Telemetry VM, test MQTT connectivity
nc -zv 192.168.5.201 1883

# Expected output:
# Connection to 192.168.5.201 1883 port [tcp/*] succeeded!
```

### Step 3: Stop Current Stack

```bash
cd /opt/seitor-tesla-telemetry

# Stop all containers (keeps volumes)
docker compose down

# Verify stopped
docker compose ps
# Should show no running containers
```

### Step 4: Update Configuration

#### 4a. Update config.json

```bash
# Edit config.json
nano config.json
```

Replace Kafka section with MQTT:

```json
{
  "host": "0.0.0.0",
  "port": 443,
  "log_level": "info",
  "json_log_enable": true,
  "namespace": "tesla_telemetry",
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  },
  "mqtt": {
    "broker": "192.168.5.201:1883",
    "client_id": "fleet-telemetry",
    "username": "",
    "password": "",
    "topic_base": "tesla",
    "qos": 1,
    "retained": true,
    "connect_timeout_ms": 30000,
    "publish_timeout_ms": 2500,
    "keep_alive_seconds": 30
  },
  "records": {
    "V": ["mqtt"],
    "alerts": ["mqtt"],
    "errors": ["mqtt"]
  },
  "reliable_ack": true,
  "reliable_ack_sources": {
    "V": "mqtt"
  },
  "rate_limit": {
    "enabled": true,
    "message_limit": 1000,
    "message_interval_time_seconds": 30
  },
  "metrics": {
    "port": 8443,
    "enabled": true
  }
}
```

#### 4b. Update docker-compose.yml

```bash
nano docker-compose.yml
```

Replace with simplified version (MQTT only):

```yaml
version: '3.8'

services:
  fleet-telemetry:
    image: tesla/fleet-telemetry:latest
    container_name: fleet-telemetry
    restart: unless-stopped
    ports:
      - "443:443"
      - "8443:8443"
    volumes:
      - ./config.json:/config.json:ro
      - ./certs:/certs:ro
      - ./keys:/keys:ro
      - ./logs:/var/log/fleet-telemetry
    environment:
      CONFIG_FILE: /config.json
      LOG_LEVEL: info
    healthcheck:
      test: ["CMD", "curl", "-f", "-k", "https://localhost:443/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  default:
    driver: bridge
```

### Step 5: Start Fleet Telemetry

```bash
# Start only fleet-telemetry (no Kafka needed)
docker compose up -d

# Check status
docker compose ps

# Watch logs for MQTT connection
docker compose logs -f fleet-telemetry
```

### Step 6: Verify MQTT Messages

```bash
# On HA Real (192.168.5.201), subscribe to Tesla topics
mosquitto_sub -h localhost -u mqtt_user -P mqtt_pass -t "tesla/#" -v

# Or check HA logs
docker logs homeassistant 2>&1 | grep -i "tesla\|mqtt" | tail -20
```

### Step 7: Verify HA Entities

Check Home Assistant for updated Tesla entities with real values.

---

## Rollback Procedure

If something goes wrong, follow these steps to restore Kafka:

### Quick Rollback (< 5 minutes)

```bash
# SSH to Fleet Telemetry VM
ssh root@192.168.5.204
cd /opt/seitor-tesla-telemetry

# Stop current containers
docker compose down

# Restore backup files
cp backup-kafka/config.json .
cp backup-kafka/docker-compose.yml .
cp backup-kafka/.env . 2>/dev/null || true

# Start Kafka stack
docker compose up -d

# Verify all services running
docker compose ps
# Should show: zookeeper, kafka, fleet-telemetry

# Check logs
docker compose logs -f fleet-telemetry
```

### Verify Rollback Success

```bash
# Check Kafka is receiving messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry_V \
  --timeout-ms 30000

# Check HA integration (should still work with Kafka v1.x)
```

### If HA Integration Was Updated

If you also updated the HA integration to v2.0.0 (MQTT), you need to:

1. Remove the MQTT integration entry from HA
2. Reinstall the Kafka version of the integration:

```bash
# On HA Real
cd /config/custom_components

# Backup current (MQTT) version
mv tesla_telemetry_local tesla_telemetry_local_mqtt_backup

# Restore Kafka version from git
git clone --branch v1.x https://github.com/jjtortosa/seitor-tesla-telemetry.git temp
cp -r temp/ha-integration/custom_components/tesla_telemetry_local .
rm -rf temp

# Restart HA
ha core restart
```

---

## Troubleshooting

### MQTT Connection Refused

```bash
# Check Mosquitto is running on HA
ssh root@192.168.5.201 "docker ps | grep mosquitto"

# Check firewall
nc -zv 192.168.5.201 1883

# Check Mosquitto logs
ssh root@192.168.5.201 "docker logs addon_core_mosquitto 2>&1 | tail -20"
```

### Fleet Telemetry Won't Start

```bash
# Check config.json syntax
python3 -c "import json; json.load(open('config.json'))"

# Check logs
docker compose logs fleet-telemetry

# Common issues:
# - Invalid JSON syntax
# - MQTT broker unreachable
# - Certificate issues
```

### No Messages in MQTT

```bash
# Verify fleet-telemetry is connected to MQTT
docker compose logs fleet-telemetry | grep -i mqtt

# Check vehicle is sending data
docker compose logs fleet-telemetry | grep -i vehicle

# Verify topic structure
mosquitto_sub -h 192.168.5.201 -t "#" -v | grep tesla
```

### HA Entities Not Updating

```bash
# Check HA integration logs
docker logs homeassistant 2>&1 | grep tesla_telemetry_local

# Verify MQTT subscription
# Look for: "Subscribed to MQTT topic: tesla/..."

# Restart integration
# HA UI → Settings → Integrations → Tesla Telemetry Local → Reload
```

---

## Verification Checklist

After migration, verify:

- [ ] Fleet Telemetry container running
- [ ] MQTT connection established (check logs)
- [ ] Messages appearing in MQTT broker
- [ ] HA entities updating with real values
- [ ] Device tracker showing correct location
- [ ] Binary sensors (charging, driving) working
- [ ] No errors in HA logs

---

## Contact Points

- **Fleet Telemetry VM**: 192.168.5.204
- **HA Real**: 192.168.5.201
- **MQTT Port**: 1883
- **Vehicle VIN**: LRWYGCFS3RC210528

## Files Location

| File | Location |
|------|----------|
| Fleet Telemetry config | `/opt/seitor-tesla-telemetry/config.json` |
| Docker Compose | `/opt/seitor-tesla-telemetry/docker-compose.yml` |
| Backup | `/opt/seitor-tesla-telemetry/backup-kafka/` |
| HA Integration | `/config/custom_components/tesla_telemetry_local/` |
| Mosquitto config | HA Add-on (Supervisor UI) |
