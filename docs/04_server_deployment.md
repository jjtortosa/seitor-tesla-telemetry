# Server Deployment

This guide covers deploying the Fleet Telemetry server stack with MQTT output.

## Prerequisites

- ✅ Server/container created with Docker installed
- ✅ DNS configured (tesla-telemetry.yourdomain.com)
- ✅ SSL certificate generated
- ✅ Port 443 forwarded
- ✅ Tesla Developer account and application created
- ✅ EC keys generated
- ✅ Virtual key paired with vehicle
- ✅ MQTT broker running in Home Assistant (Mosquitto add-on)

**Estimated time**: 1-2 hours

---

## Step 1: Clone Repository

### 1.1 SSH into Server

```bash
ssh root@your-server-ip
```

### 1.2 Clone Project

```bash
cd /opt
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git tesla-telemetry
cd tesla-telemetry/server
```

---

## Step 2: Prepare Environment

### 2.1 Create Directories

```bash
cd /opt/tesla-telemetry/server
mkdir -p keys certs logs
chmod 755 keys certs logs
```

### 2.2 Generate Cryptographic Keys

```bash
./scripts/generate_keys.sh
```

**Expected output**:
```
Generating EC private key (secp256r1 curve)...
Private key generated: keys/private_key.pem
Public key generated: keys/public_key.pem
Tesla public key: keys/com.tesla.3p.public-key.pem
```

### 2.3 Copy SSL Certificates

```bash
# Copy your SSL certificates
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem certs/

# Set permissions
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

**Verify**:
```bash
ls -la certs/
# Should show fullchain.pem and privkey.pem
```

---

## Step 3: Configure Fleet Telemetry

### 3.1 Run Interactive Setup

```bash
./setup.sh
```

The script will ask for:
- **Domain**: Your telemetry domain (e.g., `tesla-telemetry.yourdomain.com`)
- **MQTT Broker**: Home Assistant IP and port (e.g., `192.168.1.50:1883`)
- **MQTT Username/Password**: Credentials for Mosquitto
- **MQTT Topic Base**: Usually `tesla` (default)

### 3.2 Verify Configuration

Check generated files:

```bash
# Environment variables
cat .env

# Fleet Telemetry config
cat config.json
```

**config.json should include**:
```json
{
  "host": "0.0.0.0",
  "port": 443,
  "mqtt": {
    "broker": "192.168.1.50:1883",
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
  "tls": {
    "server_cert": "/certs/fullchain.pem",
    "server_key": "/certs/privkey.pem"
  }
}
```

---

## Step 4: Deploy Stack

### 4.1 Start Fleet Telemetry

```bash
docker compose up -d
```

### 4.2 Verify Container Running

```bash
docker compose ps
```

**Expected output**:
```
NAME              STATUS         PORTS
fleet-telemetry   Up (healthy)   0.0.0.0:443->443/tcp, 0.0.0.0:8443->8443/tcp
```

### 4.3 Check Logs

```bash
docker compose logs -f fleet-telemetry
```

**Look for**:
```
Server started on 0.0.0.0:443
MQTT connection established to 192.168.1.50:1883
```

---

## Step 5: Verify HTTPS Endpoint

### 5.1 Test Health Endpoint

```bash
curl -k https://localhost:443/health
```

**Expected**: `{"status": "ok"}`

### 5.2 Test External Access

From another machine:

```bash
curl -k https://tesla-telemetry.yourdomain.com/health
```

---

## Step 6: Host Public Key

Tesla needs to access your public key at:
```
https://tesla-telemetry.yourdomain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

### 6.1 Option A: Using Fleet Telemetry

Fleet Telemetry can serve the key automatically if configured in config.json:

```json
{
  "keys": {
    "public_key_path": "/keys/com.tesla.3p.public-key.pem",
    "serve_public_key": true
  }
}
```

### 6.2 Option B: Using Nginx

If using reverse proxy:

```nginx
location /.well-known/appspecific/ {
    alias /opt/tesla-telemetry/server/keys/;
}
```

### 6.3 Verify Public Key Access

```bash
curl https://tesla-telemetry.yourdomain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

Should output your public key (starting with `-----BEGIN PUBLIC KEY-----`).

---

## Step 7: Send Telemetry Config to Vehicle

### 7.1 Get OAuth Token

You'll need a valid Tesla OAuth token. Use your preferred method to obtain one.

### 7.2 Create Telemetry Config

Create file `telemetry_config.json`:

```json
{
  "vins": ["YOUR_VIN"],
  "config": {
    "hostname": "tesla-telemetry.yourdomain.com",
    "port": 443,
    "ca": "-----BEGIN CERTIFICATE-----\n...YOUR CA CERT...\n-----END CERTIFICATE-----",
    "fields": {
      "Location": { "interval_seconds": 5 },
      "VehicleSpeed": { "interval_seconds": 1 },
      "Gear": { "interval_seconds": 1 },
      "Soc": { "interval_seconds": 60 },
      "ChargeState": { "interval_seconds": 30 },
      "InsideTemp": { "interval_seconds": 60 },
      "OutsideTemp": { "interval_seconds": 60 },
      "TpmsPressureFl": { "interval_seconds": 60 },
      "TpmsPressureFr": { "interval_seconds": 60 },
      "TpmsPressureRl": { "interval_seconds": 60 },
      "TpmsPressureRr": { "interval_seconds": 60 },
      "Odometer": { "interval_seconds": 300 }
    },
    "alert_types": ["service"]
  }
}
```

### 7.3 Send Config to Tesla

```bash
curl -X POST "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/YOUR_VEHICLE_ID/fleet_telemetry_config" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d @telemetry_config.json
```

**Expected response**:
```json
{"response": {"synced": true}}
```

---

## Step 8: Verify Vehicle Connection

### 8.1 Monitor Fleet Telemetry Logs

```bash
docker compose logs -f fleet-telemetry
```

**Look for**:
```
New vehicle connection from VIN: YOUR_VIN
Message published to MQTT: tesla/YOUR_VIN/v/VehicleSpeed
```

### 8.2 Monitor MQTT Messages

From Home Assistant terminal:

```bash
mosquitto_sub -h localhost -t "tesla/#" -v
```

**Expected output**:
```
tesla/YOUR_VIN/v/BatteryLevel {"value": 78}
tesla/YOUR_VIN/v/VehicleSpeed {"value": 0}
tesla/YOUR_VIN/v/Location {"latitude": 41.38, "longitude": 2.17}
```

### 8.3 Trigger Vehicle Activity

To generate messages:
1. Open Tesla app
2. Turn on climate control
3. Unlock/lock doors

---

## Step 9: Useful Commands

### Start/Stop

```bash
docker compose up -d      # Start
docker compose down       # Stop
docker compose restart    # Restart
```

### Logs

```bash
docker compose logs -f fleet-telemetry
```

### Update

```bash
docker compose pull
docker compose up -d
```

---

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
./scripts/validate_cert.sh tesla-telemetry.yourdomain.com

# Check certificate dates
openssl x509 -in certs/fullchain.pem -noout -dates
```

### MQTT connection failed

```bash
# Test MQTT connectivity from server
nc -zv 192.168.1.50 1883

# Check MQTT credentials
# Verify username/password in config.json match Mosquitto add-on
```

### Vehicle not connecting

1. Check virtual key is paired: Tesla app → Vehicle → Keys
2. Verify telemetry config was sent successfully
3. Check DNS resolves correctly: `nslookup tesla-telemetry.yourdomain.com`
4. Ensure port 443 is accessible from internet

---

## Validation Checklist

Before proceeding to HA integration:

- [ ] Fleet Telemetry container running and healthy
- [ ] MQTT connection established (check logs)
- [ ] Public key accessible via HTTPS
- [ ] Vehicle telemetry config sent successfully
- [ ] MQTT messages arriving (mosquitto_sub shows data)
- [ ] No errors in Fleet Telemetry logs

---

## Next Steps

Server deployment complete! Proceed to:

**[05 - Home Assistant Integration →](05_ha_integration.md)**

This will guide you through installing the custom HA component to consume MQTT messages and create entities.
