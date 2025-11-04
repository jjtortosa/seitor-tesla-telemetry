# Server Deployment

This guide covers deploying the Fleet Telemetry server stack on your Proxmox container.

## Prerequisites

- ✅ Proxmox container created with Docker installed
- ✅ DNS configured (tesla-telemetry.seitor.com)
- ✅ SSL certificate generated
- ✅ Port 443 forwarded
- ✅ Tesla Developer account and application created
- ✅ EC keys generated
- ✅ Virtual key paired with vehicle

**Estimated time**: 3-4 hours (includes testing and vehicle connection)

---

## Step 1: Clone Repository to Server

### 1.1 SSH into Proxmox Container

```bash
# From Proxmox host
pct enter 105

# Or via SSH
ssh root@192.168.5.105
```

### 1.2 Clone Project Repository

```bash
# Navigate to project directory
cd /opt

# Clone repository
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git tesla-telemetry

# Navigate to server directory
cd tesla-telemetry/server
```

---

## Step 2: Prepare Directories and Files

### 2.1 Create Required Directories

```bash
cd /opt/tesla-telemetry/server

# Create directories
mkdir -p keys certs logs kafka-data zookeeper-data

# Set permissions
chmod 755 keys certs logs
chmod 700 kafka-data zookeeper-data
```

### 2.2 Generate Cryptographic Keys

```bash
# Run key generation script
./scripts/generate_keys.sh
```

**Expected output**:
```
🔐 Tesla Fleet API Key Generation
==================================

📝 Generating EC private key (secp256r1 curve)...
✅ Private key generated: keys/private_key.pem

📝 Deriving public key...
✅ Public key generated: keys/public_key.pem

📝 Creating Tesla-specific public key format...
✅ Tesla public key: keys/com.tesla.3p.public-key.pem

✅ Key generation complete!
```

⚠️ **Verify keys exist**:
```bash
ls -la keys/
```

Should show:
- `private_key.pem` (600 permissions)
- `public_key.pem` (644 permissions)
- `com.tesla.3p.public-key.pem` (644 permissions)

### 2.3 Copy SSL Certificates

**Option A: Symlink** (recommended if using certbot auto-renewal):

```bash
ln -s /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem certs/fullchain.pem
ln -s /etc/letsencrypt/live/tesla-telemetry.seitor.com/privkey.pem certs/privkey.pem
```

**Option B: Copy**:

```bash
cp /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem certs/
cp /etc/letsencrypt/live/tesla-telemetry.seitor.com/privkey.pem certs/
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

**Verify**:
```bash
ls -la certs/
```

### 2.4 Host Public Key for Tesla

Ensure Nginx is serving the public key at the required URL.

**Copy key to web directory**:

```bash
mkdir -p /var/www/tesla-telemetry/.well-known/appspecific
cp keys/com.tesla.3p.public-key.pem /var/www/tesla-telemetry/.well-known/appspecific/
chmod 644 /var/www/tesla-telemetry/.well-known/appspecific/com.tesla.3p.public-key.pem
```

**Test accessibility**:

```bash
# From server
curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem

# From outside network (use phone or https://reqbin.com/)
curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

Expected output:
```
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
-----END PUBLIC KEY-----
```

---

## Step 3: Configure Fleet Telemetry Server

### 3.1 Create Configuration File

```bash
cd /opt/tesla-telemetry/server

# Copy example config
cp config.json.example config.json

# Edit configuration
nano config.json
```

**Minimal configuration**:

```json
{
  "host": "tesla-telemetry.seitor.com",
  "port": 443,
  "log_level": "info",
  "json_log_enable": true,
  "namespace": "tesla",
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  },
  "kafka": {
    "brokers": ["kafka:9092"],
    "topic": "tesla_telemetry"
  },
  "rate_limit": {
    "enabled": true,
    "message_limit": 1000,
    "message_interval_time_seconds": 30
  },
  "reliable_ack": true,
  "reliable_ack_sources": {
    "source_names": ["kafka"]
  },
  "metrics": {
    "port": 8443,
    "enabled": true,
    "namespace": "tesla_telemetry"
  }
}
```

**Key settings**:
- **host**: Your domain (tesla-telemetry.seitor.com)
- **tls.server_cert**: Path to SSL certificate (inside container: `/certs/fullchain.pem`)
- **tls.server_key**: Path to SSL private key (inside container: `/certs/privkey.pem`)
- **kafka.brokers**: Kafka broker address (`kafka:9092` uses Docker network)
- **rate_limit**: Prevent vehicle from overwhelming server

### 3.2 Create Environment File (Optional)

For sensitive configuration:

```bash
nano .env
```

**Content**:
```env
# Tesla API Credentials
TESLA_CLIENT_ID=ta-12345abcdefghijklmn
TESLA_CLIENT_SECRET=ts-secret-your-secret-here
TESLA_VEHICLE_ID=1234567890123456789

# Domain
TESLA_DOMAIN=tesla-telemetry.seitor.com

# Log level
LOG_LEVEL=info
```

**Set permissions**:
```bash
chmod 600 .env
```

---

## Step 4: Start Docker Stack

### 4.1 Pull Docker Images

```bash
cd /opt/tesla-telemetry/server

# Pull all images
docker compose pull
```

**Expected output**:
```
Pulling zookeeper       ... done
Pulling kafka           ... done
Pulling fleet-telemetry ... done
Pulling kafka-ui        ... done
```

### 4.2 Start Services

```bash
# Start in background
docker compose up -d

# Or start with logs visible (for debugging first time)
docker compose up
```

**Expected output**:
```
Creating network "server_tesla-net" ... done
Creating volume "server_zookeeper-data" ... done
Creating volume "server_kafka-data" ... done
Creating zookeeper ... done
Creating kafka     ... done
Creating fleet-telemetry ... done
Creating kafka-ui  ... done
```

### 4.3 Verify Services are Running

```bash
docker compose ps
```

**Expected output**:
```
NAME               STATUS              PORTS
fleet-telemetry    Up 30 seconds       0.0.0.0:443->443/tcp, 0.0.0.0:8443->8443/tcp
kafka              Up 45 seconds       0.0.0.0:9092->9092/tcp, 0.0.0.0:29092->29092/tcp
kafka-ui           Up 15 seconds       0.0.0.0:8080->8080/tcp
zookeeper          Up 1 minute         2181/tcp
```

All containers should show **"Up"** status with **healthy** state.

### 4.4 Check Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f fleet-telemetry

# Last 50 lines
docker compose logs --tail=50 fleet-telemetry
```

**Look for**:
- ✅ `Fleet Telemetry server started on :443`
- ✅ `Kafka connection established`
- ✅ `TLS certificate loaded`
- ❌ Any ERROR messages

---

## Step 5: Validate Certificate

### 5.1 Run Certificate Validation Script

```bash
cd /opt/tesla-telemetry/server

./scripts/validate_cert.sh tesla-telemetry.seitor.com
```

**Expected output**:
```
🔐 SSL Certificate Validation for Tesla Fleet Telemetry
=========================================================

Domain: tesla-telemetry.seitor.com
Port: 443

📡 Checking DNS resolution...
✅ Domain resolves to: 93.45.123.45

🔌 Checking port 443 connectivity...
✅ Port 443 is accessible

🔍 Fetching SSL certificate...
✅ Certificate retrieved

📋 Certificate Details:
----------------------
subject=CN = tesla-telemetry.seitor.com
issuer=C = US, O = Let's Encrypt, CN = R3

⏱️  Certificate Expiry:
   Expires: Jan 15 12:00:00 2026 GMT
   Days until expiry: 72
   ✅ Certificate valid

✅ Certificate CN matches domain: tesla-telemetry.seitor.com
📜 Certificate Issuer: C = US, O = Let's Encrypt, CN = R3
   ✅ Trusted CA

🤝 Testing TLS handshake...
✅ TLS handshake successful

🔐 Checking TLS versions...
   ✅ TLS 1.2 supported
   ✅ TLS 1.3 supported

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Validation Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ All checks passed!
   Certificate is valid for Tesla Fleet Telemetry
```

### 5.2 Test Health Endpoint

```bash
# From server
curl http://localhost:8443/health

# Expected output
OK
```

```bash
# From outside network
curl https://tesla-telemetry.seitor.com:8443/health

# Expected output
OK
```

---

## Step 6: Configure Tesla Vehicle Telemetry

### 6.1 Create Telemetry Configuration

Create a JSON file specifying which data fields to stream:

```bash
cd /opt/tesla-telemetry/server

nano telemetry_config.json
```

**Content**:

```json
{
  "hostname": "tesla-telemetry.seitor.com",
  "ca": "letsencrypt",
  "fields": {
    "Location": {
      "interval_seconds": 5
    },
    "Latitude": {
      "interval_seconds": 5
    },
    "Longitude": {
      "interval_seconds": 5
    },
    "Heading": {
      "interval_seconds": 5
    },
    "ShiftState": {
      "interval_seconds": 1
    },
    "Speed": {
      "interval_seconds": 1
    },
    "Soc": {
      "interval_seconds": 60
    },
    "EstBatteryRange": {
      "interval_seconds": 60
    },
    "ChargingState": {
      "interval_seconds": 30
    },
    "ChargePortDoorOpen": {
      "interval_seconds": 30
    },
    "ChargerActualCurrent": {
      "interval_seconds": 30
    },
    "ChargerVoltage": {
      "interval_seconds": 30
    }
  }
}
```

**Field explanations**:
- **Location/Latitude/Longitude/Heading**: GPS data (5s = real-time)
- **ShiftState**: Gear (P/D/R/N) - 1s for instant detection
- **Speed**: Current speed - 1s
- **Soc**: Battery % - 60s (once per minute)
- **EstBatteryRange**: Range estimate - 60s
- **ChargingState**: Charging status - 30s
- **Charging fields**: Voltage, current - 30s

### 6.2 Send Configuration to Vehicle

**Method 1: Using Tesla Fleet API directly**

First, get an access token (if not already done):

```bash
# Exchange authorization code for token (see docs/03_tesla_developer_setup.md step 7)
# Save tokens in tesla_tokens.json
```

Then send config:

```bash
# Get vehicle ID
VEHICLE_ID=$(cat .env | grep TESLA_VEHICLE_ID | cut -d '=' -f2)

# Get access token
ACCESS_TOKEN=$(cat tesla_tokens.json | jq -r '.access_token')

# Send telemetry config
curl -X POST \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/command/fleet_telemetry_config" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @telemetry_config.json
```

**Expected response**:
```json
{
  "response": {
    "result": true,
    "reason": ""
  }
}
```

**Method 2: Using `vehicle-command` proxy (recommended)**

Tesla provides a separate `vehicle-command` Docker image for sending commands:

```bash
# Add vehicle-command service to docker-compose.yml (see below)
# Then use it to send config
```

### 6.3 Verify Configuration Applied

Check vehicle receives configuration:

```bash
# Monitor fleet-telemetry logs for connection
docker compose logs -f fleet-telemetry | grep -i "telemetry\|connection\|vehicle"
```

**Look for**:
- `Telemetry config received from vehicle`
- `Vehicle connected: VIN=5YJ3E1EA1MF000000`

---

## Step 7: Test Vehicle Connection

### 7.1 Wake Up Vehicle

Using Tesla app, wake up your vehicle (open app → vehicle should wake).

Alternatively, use Fleet API:

```bash
curl -X POST \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/command/wake_up" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```

### 7.2 Monitor Logs for Connection

```bash
docker compose logs -f fleet-telemetry
```

**Expected log entries** (when vehicle connects):
```
INFO  Vehicle connecting from IP: 93.45.67.89
INFO  TLS handshake successful, client cert validated
INFO  Vehicle authenticated: VIN=5YJ3E1EA1MF000000
INFO  Starting telemetry stream for vehicle
INFO  Received telemetry message: Location, Speed, ShiftState
INFO  Message published to Kafka topic: tesla_telemetry
```

### 7.3 Check Kafka Topics

```bash
# List topics (should see tesla_telemetry)
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Expected output:
# tesla_telemetry
# (possibly others like __consumer_offsets, etc.)
```

### 7.4 Consume Test Messages

```bash
# Read messages from Kafka topic
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --from-beginning \
  --max-messages 10
```

**Expected output** (binary Protobuf data, not human-readable):
```
^@^@^@...^@^@^@...
```

If you see messages, **streaming is working**! 🎉

---

## Step 8: Access Kafka UI (Optional)

### 8.1 Open Kafka UI

Open browser and navigate to:
```
http://192.168.5.105:8080
```

(Replace IP with your container IP)

### 8.2 View Topics and Messages

1. Click **"Topics"** in left sidebar
2. Find **"tesla_telemetry"** topic
3. Click **"Messages"** tab
4. View incoming messages in real-time

**What you'll see**:
- Message offset (incrementing as new messages arrive)
- Timestamp
- Key (usually empty or VIN)
- Value (binary Protobuf data)

---

## Step 9: Monitoring and Metrics

### 9.1 Fleet Telemetry Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8443/metrics

# Expected output (Prometheus format):
# fleet_telemetry_messages_received_total{vehicle_id="123456"} 1542
# fleet_telemetry_messages_published_total{topic="tesla_telemetry"} 1542
# fleet_telemetry_connections_active 1
```

### 9.2 Create Monitoring Dashboard (Optional)

**Using Grafana**:

Add Grafana to `docker-compose.yml`:

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: grafana
  restart: unless-stopped
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafana-data:/var/lib/grafana
  networks:
    - tesla-net
```

Then:
1. Access Grafana at http://192.168.5.105:3000
2. Add Prometheus data source: http://fleet-telemetry:8443
3. Import Tesla Telemetry dashboard (create custom or find community dashboard)

---

## Step 10: Automate Token Refresh (Important!)

Tesla access tokens expire after 8 hours. Set up automatic refresh.

### 10.1 Create Refresh Script

```bash
nano /opt/tesla-telemetry/server/scripts/refresh_token.sh
```

**Content**:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
TOKENS_FILE="$SERVER_DIR/tesla_tokens.json"
ENV_FILE="$SERVER_DIR/.env"

# Load credentials
source "$ENV_FILE"

# Read current refresh token
REFRESH_TOKEN=$(jq -r '.refresh_token' "$TOKENS_FILE")

# Request new access token
RESPONSE=$(curl -s -X POST https://auth.tesla.com/oauth2/v3/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "client_id=$TESLA_CLIENT_ID" \
  -d "client_secret=$TESLA_CLIENT_SECRET" \
  -d "refresh_token=$REFRESH_TOKEN")

# Extract new tokens
NEW_ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
NEW_REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')
EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')
EXPIRES_AT=$(($(date +%s) + EXPIRES_IN))

# Update tokens file
jq --arg access "$NEW_ACCESS_TOKEN" \
   --arg refresh "$NEW_REFRESH_TOKEN" \
   --arg expires "$EXPIRES_AT" \
   '.access_token = $access | .refresh_token = $refresh | .expires_at = $expires' \
   "$TOKENS_FILE" > "$TOKENS_FILE.tmp" && mv "$TOKENS_FILE.tmp" "$TOKENS_FILE"

echo "✅ Token refreshed successfully. Expires at: $(date -d @$EXPIRES_AT)"
```

**Make executable**:
```bash
chmod +x /opt/tesla-telemetry/server/scripts/refresh_token.sh
```

### 10.2 Schedule with Cron

```bash
crontab -e
```

**Add line** (refresh every 6 hours):
```cron
0 */6 * * * /opt/tesla-telemetry/server/scripts/refresh_token.sh >> /opt/tesla-telemetry/server/logs/token_refresh.log 2>&1
```

---

## Step 11: Validation Checklist

Before proceeding to Home Assistant integration, verify:

- ✅ Docker stack running (all containers healthy)
- ✅ Nginx serving public key at `.well-known` URL
- ✅ SSL certificate valid (validated with script)
- ✅ Port 443 accessible from internet
- ✅ Telemetry config sent to vehicle
- ✅ Vehicle connected to fleet-telemetry (check logs)
- ✅ Messages arriving in Kafka topic
- ✅ Kafka UI showing telemetry messages
- ✅ Token refresh automated

---

## Troubleshooting

### Container won't start

**Problem**: `docker compose up` fails

**Check**:
```bash
docker compose logs fleet-telemetry

# Common issues:
# - Invalid config.json syntax
# - Missing certificates (certs/fullchain.pem, certs/privkey.pem)
# - Port 443 already in use
```

**Solutions**:
1. Validate config.json: `jq . config.json`
2. Check certificates exist: `ls -la certs/`
3. Check port: `netstat -tulpn | grep 443`

### Vehicle not connecting

**Problem**: No connection logs in fleet-telemetry

**Check**:
1. Virtual key paired: Tesla app → Keys
2. Telemetry config sent and accepted
3. Vehicle has internet connectivity
4. Port 443 accessible from outside: `nc -zv tesla-telemetry.seitor.com 443` (from phone hotspot)

**Debug**:
```bash
# Enable debug logging
# Edit config.json: "log_level": "debug"
docker compose restart fleet-telemetry
docker compose logs -f fleet-telemetry
```

### Kafka not receiving messages

**Problem**: Kafka topic empty despite vehicle connected

**Check**:
```bash
# Check Kafka is healthy
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Check topic exists
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Check fleet-telemetry Kafka connection
docker compose logs fleet-telemetry | grep -i kafka
```

**Solution**:
- Restart Kafka: `docker compose restart kafka`
- Verify config.json kafka.brokers is correct: `"kafka:9092"`

### Certificate errors

**Problem**: TLS handshake failures in logs

**Solutions**:
1. Validate certificate: `./scripts/validate_cert.sh tesla-telemetry.seitor.com`
2. Check certificate not expired: `openssl x509 -in certs/fullchain.pem -noout -enddate`
3. Regenerate if needed: `certbot renew --force-renewal`

---

## Next Steps

Server deployment complete! Your Tesla is now streaming data to Kafka.

Proceed to:

**[05 - Home Assistant Integration →](05_ha_integration.md)**

This will guide you through installing the custom HA component to consume Kafka messages and create entities.
