# Demo Environment Setup

Complete guide to set up the public demo at `demo.seitor.com`.

## Architecture

```
Internet → Cloudflare → Nginx Proxy Manager → HA Test
                ↓              ↓                 ↓
         demo.seitor.com   192.168.5.201    192.168.6.41:8123
                           (NPM)            (Home Assistant)
                                                  ↓
                                            Mock Telemetry
                                            (MQTT simulator)
```

## Prerequisites

- [x] HA Test VM running (192.168.6.41)
- [x] Nginx Proxy Manager running (192.168.5.201:81)
- [x] Cloudflare managing seitor.com
- [x] Public IP accessible from internet

## Step 1: Configure Cloudflare DNS

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select `seitor.com` domain
3. Go to **DNS** → **Records**
4. Add new record:
   - **Type**: CNAME
   - **Name**: demo
   - **Target**: seitor.com (or your A record)
   - **Proxy status**: Proxied (orange cloud) ✅
   - **TTL**: Auto

Or use Cloudflare API:
```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/YOUR_ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "demo",
    "content": "seitor.com",
    "proxied": true
  }'
```

## Step 2: Configure Nginx Proxy Manager

1. Access NPM: http://192.168.5.201:81
2. Go to **Proxy Hosts** → **Add Proxy Host**
3. Configure:

   **Details tab:**
   - Domain Names: `demo.seitor.com`
   - Scheme: `http`
   - Forward Hostname/IP: `192.168.6.41`
   - Forward Port: `8123`
   - Cache Assets: ❌
   - Block Common Exploits: ✅
   - Websockets Support: ✅ (required for HA)

   **SSL tab:**
   - SSL Certificate: Request new or use `*.seitor.com` wildcard
   - Force SSL: ✅
   - HTTP/2 Support: ✅

4. Save

## Step 3: Install Integration on HA Test

SSH into HA Test and run:

```bash
# From your Mac
ssh root@192.168.6.41

# On HA Test - download and install integration
cd /config
mkdir -p custom_components
cd custom_components

# Clone or copy the integration
git clone https://github.com/jjtortosa/seitor-tesla-telemetry.git temp
mv temp/custom_components/tesla_telemetry_local .
rm -rf temp

# Restart Home Assistant
ha core restart
```

Or copy directly from your Mac:
```bash
scp -r /Users/juanjo/Projects/seitor-tesla-telemetry/custom_components/tesla_telemetry_local root@192.168.6.41:/config/custom_components/
```

## Step 4: Configure MQTT on HA Test

1. Install Mosquitto add-on in HA Test:
   - Settings → Add-ons → Add-on Store
   - Search "Mosquitto broker" → Install → Start

2. Configure MQTT integration:
   - Settings → Devices & Services → Add Integration
   - Search "MQTT" → Configure
   - Use default settings (broker: localhost)

## Step 5: Start Mock Telemetry Generator

SSH into HA Test:

```bash
# Install Python and dependencies
apk add python3 py3-pip
pip3 install paho-mqtt

# Copy the mock script
scp /Users/juanjo/Projects/seitor-tesla-telemetry/tools/demo/mock_telemetry.py root@192.168.6.41:/root/

# Run in background
cd /root
nohup python3 mock_telemetry.py \
  --mqtt-host localhost \
  --mqtt-port 1883 \
  --vin DEMO0TESLA0VIN00 \
  --scenario driving \
  --duration 86400 \
  --interval 5 \
  --continuous &
```

Or create a systemd service:

```bash
cat > /etc/systemd/system/tesla-mock.service << 'EOF'
[Unit]
Description=Tesla Mock Telemetry
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/mock_telemetry.py --mqtt-host localhost --vin DEMO0TESLA0VIN00 --scenario driving --continuous
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl enable tesla-mock
systemctl start tesla-mock
```

## Step 6: Configure Demo Integration in HA

1. Go to https://demo.seitor.com
2. Complete HA onboarding if needed
3. Settings → Devices & Services → Add Integration
4. Search "Tesla Fleet Telemetry Local"
5. Configure:
   - MQTT Topic Base: `tesla`
   - Vehicle VIN: `DEMO0TESLA0VIN00`
   - Vehicle Name: `Demo Tesla`

## Step 7: Create Demo Dashboard

Create a demo-specific dashboard showing:

1. **Map card** with device_tracker
2. **Gauge cards** for battery, speed
3. **Entity cards** for all sensors (read-only integration)

Example Lovelace configuration:

```yaml
title: Tesla Demo
views:
  - title: Demo Tesla
    path: demo
    icon: mdi:car-electric
    cards:
      - type: map
        entities:
          - device_tracker.demo_tesla_location
        default_zoom: 14

      - type: gauge
        entity: sensor.demo_tesla_battery
        name: Battery
        min: 0
        max: 100
        severity:
          green: 50
          yellow: 20
          red: 10

      - type: gauge
        entity: sensor.demo_tesla_speed
        name: Speed
        min: 0
        max: 150
        unit: km/h

      - type: entities
        title: Vehicle Status
        entities:
          - sensor.demo_tesla_shift_state
          - sensor.demo_tesla_range
          - sensor.demo_tesla_charging_state
          - binary_sensor.demo_tesla_awake
          - binary_sensor.demo_tesla_driving

      - type: entities
        title: Climate
        entities:
          - sensor.demo_tesla_inside_temp
          - sensor.demo_tesla_outside_temp

      - type: entities
        title: Tire Pressure
        entities:
          - sensor.demo_tesla_tpms_front_left
          - sensor.demo_tesla_tpms_front_right
          - sensor.demo_tesla_tpms_rear_left
          - sensor.demo_tesla_tpms_rear_right
```

## Step 8: Security for Public Demo

### Option A: Read-only Demo User

Create a restricted user in HA:
1. Settings → People → Add Person
2. Name: `Demo Visitor`
3. Allow login: Yes
4. Create user with limited permissions

### Option B: Kiosk Mode (recommended)

Install HACS, then install `kiosk-mode`:

```yaml
# configuration.yaml
kiosk_mode:
  non_admin_user: true
```

**Note:** The integration is read-only (sensors only), so no vehicle controls to hide.

## Verification

1. Check DNS:
   ```bash
   nslookup demo.seitor.com
   ```

2. Check HTTPS:
   ```bash
   curl -I https://demo.seitor.com
   ```

3. Check HA:
   Open https://demo.seitor.com in browser

4. Check mock data:
   ```bash
   mosquitto_sub -h 192.168.6.41 -t "tesla/#" -v
   ```

## Troubleshooting

### DNS not resolving
- Check Cloudflare DNS propagation (can take up to 5 min)
- Verify CNAME record is correct

### SSL certificate error
- Check NPM has valid certificate
- Force SSL is enabled

### HA not accessible
- Check HA Test VM is running: `ping 192.168.6.41`
- Check port forwarding in NPM
- Check Websockets is enabled

### No telemetry data
- Check mock script is running: `ps aux | grep mock_telemetry`
- Check MQTT: `mosquitto_sub -t "tesla/#" -v`
- Check HA logs for MQTT errors

## URLs

- **Public Demo**: https://demo.seitor.com
- **NPM Admin**: http://192.168.5.201:81
- **HA Test Direct**: http://192.168.6.41:8123
