# Fleet Telemetry Server

Docker-based Tesla Fleet Telemetry server with Kafka message queue.

## Quick Start (Recommended)

### 1. Run Interactive Setup

```bash
./setup.sh
```

This will guide you through:
- Domain configuration
- Kafka network settings
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

### 2. Generate Keys

```bash
./scripts/generate_keys.sh
```

### 3. Prepare SSL Certificates

```bash
mkdir -p certs
# Copy your certificates:
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

### 4. Start Services

```bash
docker compose up -d
```

### 5. Access Kafka UI (optional)

```bash
# Start with debug profile
docker compose --profile debug up -d
# Open http://localhost:8080
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
- **Port**: 443 (HTTPS)
- **Purpose**: Receives telemetry data from Tesla vehicles
- **Healthcheck**: http://localhost:8443/health

### kafka
- **Port**: 9092 (internal), 29092 (external)
- **Purpose**: Message queue for telemetry data
- **Topics**: `tesla_telemetry` (auto-created)

### zookeeper
- **Port**: 2181
- **Purpose**: Kafka coordination service

### kafka-ui (optional)
- **Port**: 8080
- **Purpose**: Web UI for monitoring Kafka

## Useful Commands

### Start/Stop

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart fleet-telemetry

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f fleet-telemetry
```

### Debugging

```bash
# Check Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Consume messages from topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --from-beginning

# Check fleet-telemetry metrics
curl http://localhost:8443/metrics

# Check health
curl http://localhost:8443/health
```

### Maintenance

```bash
# Update images
docker compose pull
docker compose up -d

# Clean up old data
docker compose down -v  # ⚠️ Deletes volumes (Kafka data)

# Backup Kafka data
docker run --rm -v server_kafka-data:/data -v $(pwd):/backup ubuntu tar czf /backup/kafka-backup.tar.gz /data
```

## Configuration

Edit `config.json` to customize:

- **host**: Your domain (tesla-telemetry.seitor.com)
- **tls**: Path to SSL certificates
- **kafka.brokers**: Kafka broker addresses
- **rate_limit**: Message rate limiting
- **log_level**: debug, info, warn, error

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

# Regenerate Let's Encrypt cert
certbot renew --force-renewal
```

### Kafka not receiving messages

```bash
# Check if fleet-telemetry is running
docker compose ps

# Check fleet-telemetry logs for connection errors
docker compose logs fleet-telemetry | grep -i error

# Verify Kafka is healthy
docker compose ps kafka
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092
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
