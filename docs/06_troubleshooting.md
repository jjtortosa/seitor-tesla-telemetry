# Troubleshooting Guide

Comprehensive troubleshooting guide for Tesla Fleet Telemetry self-hosted system with MQTT.

## Quick Diagnostics

### System Health Check

Run this command on your server to get overall system status:

```bash
cd /opt/tesla-telemetry/server

# Check all services
docker compose ps

# Check logs for errors
docker compose logs --tail=100 | grep -i error

# Test MQTT connectivity
mosquitto_sub -h YOUR_MQTT_BROKER -t "tesla/#" -v -C 1

# Test certificate
./scripts/validate_cert.sh tesla-telemetry.yourdomain.com

# Check fleet-telemetry health
curl -k https://localhost:443/health
```

**Healthy system output**:
- Fleet Telemetry container: `Up` + `healthy`
- No ERROR messages in logs
- MQTT broker reachable
- Certificate validation passes
- Health endpoint returns: `{"status": "ok"}`

---

## Infrastructure Issues

### DNS Not Resolving

**Symptoms**:
- `nslookup tesla-telemetry.yourdomain.com` fails
- Cannot access domain from browser
- Certificate validation fails with DNS error

**Diagnosis**:

```bash
# Test DNS resolution
nslookup tesla-telemetry.yourdomain.com

# Test from different DNS server
nslookup tesla-telemetry.yourdomain.com 8.8.8.8

# Check DNS propagation
dig tesla-telemetry.yourdomain.com +trace
```

**Solutions**:

1. **Wait for propagation** (5-30 minutes for new records)
2. **Check DNS record** at registrar/Cloudflare:
   - Type: A
   - Name: tesla-telemetry
   - Value: Your public IP
   - TTL: 300 (5 minutes)
3. **Update DDNS** if dynamic IP changed:
   ```bash
   systemctl restart ddclient
   journalctl -u ddclient -f
   ```
4. **Flush local DNS cache**:
   ```bash
   # Linux
   sudo systemd-resolve --flush-caches

   # macOS
   sudo dscacheutil -flushcache
   ```

---

### Port 443 Not Accessible

**Symptoms**:
- `nc -zv tesla-telemetry.yourdomain.com 443` fails from outside network
- Certificate validation fails on connectivity
- Vehicle cannot connect

**Diagnosis**:

```bash
# Test from server (should work)
nc -zv localhost 443

# Test from LAN (should work)
nc -zv 192.168.1.50 443

# Test from outside (use phone hotspot or https://www.yougetsignal.com/tools/open-ports/)
nc -zv tesla-telemetry.yourdomain.com 443
```

**Solutions**:

1. **Check port forwarding on router**:
   - Rule: WAN 443 → LAN 192.168.1.50:443
   - Protocol: TCP
   - Enabled: ✅

2. **Check firewall on container**:
   ```bash
   ufw status
   # Should show: 443/tcp ALLOW Anywhere
   ```

3. **Check Docker is listening**:
   ```bash
   netstat -tulpn | grep 443
   # Should show: docker-proxy listening on 0.0.0.0:443
   ```

4. **Check ISP blocking**:
   - Some ISPs block port 443 for residential users
   - Test with alternative port (e.g., 8443)
   - Contact ISP if blocked

5. **Check double NAT**:
   ```bash
   # On router, check if WAN IP is public
   # Compare with: curl ifconfig.me
   # If different, you have double NAT
   ```

---

### SSL Certificate Issues

**Symptoms**:
- Certificate validation fails
- TLS handshake errors in logs
- Vehicle connection refused

**Diagnosis**:

```bash
# Validate certificate
./scripts/validate_cert.sh tesla-telemetry.yourdomain.com

# Check certificate details
openssl s_client -connect tesla-telemetry.yourdomain.com:443 -servername tesla-telemetry.yourdomain.com

# Check certificate files exist
ls -la certs/
```

**Solutions**:

1. **Certificate expired**:
   ```bash
   # Check expiry
   openssl x509 -in certs/fullchain.pem -noout -enddate

   # Renew certificate
   certbot renew --force-renewal

   # Restart fleet-telemetry
   docker compose restart fleet-telemetry
   ```

2. **Wrong certificate path**:
   ```bash
   # Check config.json points to correct paths
   grep -A 3 '"tls"' config.json

   # Should show:
   # "server_cert": "/certs/fullchain.pem"
   # "server_key": "/certs/privkey.pem"
   ```

3. **Certificate not trusted**:
   - Ensure using Let's Encrypt or other trusted CA
   - Self-signed certificates won't work with Tesla

4. **Permissions incorrect**:
   ```bash
   chmod 644 certs/fullchain.pem
   chmod 600 certs/privkey.pem
   ```

---

## Docker Issues

### Container Won't Start

**Symptoms**:
- `docker compose up` fails
- Container exits immediately
- Status shows: `Exited (1)`

**Diagnosis**:

```bash
# Check container logs
docker compose logs fleet-telemetry

# Check for specific errors
docker compose logs fleet-telemetry | grep -i "error\|fatal\|panic"

# Try running interactively
docker compose run --rm fleet-telemetry sh
```

**Common Causes**:

1. **Invalid config.json**:
   ```bash
   # Validate JSON syntax
   jq . config.json

   # If error, fix syntax and try again
   ```

2. **Missing certificates**:
   ```bash
   # Check files exist
   ls -la certs/fullchain.pem certs/privkey.pem

   # If missing, copy from Let's Encrypt
   cp /etc/letsencrypt/live/tesla-telemetry.yourdomain.com/*.pem certs/
   ```

3. **Port already in use**:
   ```bash
   # Check if something else uses port 443
   netstat -tulpn | grep 443

   # Kill process or change port
   ```

4. **MQTT broker not reachable**:
   ```bash
   # Test MQTT connectivity from server
   nc -zv 192.168.1.50 1883

   # Check if credentials are correct in config.json
   ```

---

### MQTT Connection Issues

**Symptoms**:
- Fleet-telemetry logs: `MQTT connection failed`
- No messages arriving at MQTT broker
- Home Assistant not receiving data

**Diagnosis**:

```bash
# Check MQTT broker is accessible
nc -zv 192.168.1.50 1883

# Test MQTT connection with mosquitto
mosquitto_sub -h 192.168.1.50 -t "test/#" -v

# Check fleet-telemetry logs for MQTT errors
docker compose logs fleet-telemetry | grep -i "mqtt\|broker\|connect"
```

**Solutions**:

1. **MQTT broker not running**:
   ```bash
   # Check Mosquitto add-on in Home Assistant
   # Settings → Add-ons → Mosquitto broker → Check status

   # Or from HA terminal
   ha addons info core_mosquitto
   ```

2. **Invalid credentials**:
   ```bash
   # Test credentials manually
   mosquitto_sub -h 192.168.1.50 -u mqtt_user -P mqtt_password -t "test"

   # If fails, check Mosquitto add-on configuration for correct username/password
   ```

3. **Firewall blocking port 1883**:
   ```bash
   # On MQTT broker host (HA)
   ufw allow 1883/tcp

   # Or check if Mosquitto is binding to all interfaces
   # In Mosquitto config: listener 1883 0.0.0.0
   ```

4. **Wrong broker address**:
   ```bash
   # Check config.json has correct MQTT broker address
   grep -A 5 '"mqtt"' config.json

   # Should match your Home Assistant IP
   ```

5. **Network connectivity**:
   ```bash
   # From fleet-telemetry server, ping MQTT broker
   ping -c 3 192.168.1.50

   # Check Docker network
   docker network ls
   docker network inspect server_tesla-net
   ```

---

## Tesla Vehicle Issues

### Vehicle Not Connecting

**Symptoms**:
- No connection logs in fleet-telemetry
- No messages arriving at MQTT broker
- Vehicle shows connected in Tesla app but not to telemetry

**Diagnosis**:

```bash
# Enable debug logging
# Edit config.json: "log_level": "debug"
docker compose restart fleet-telemetry

# Monitor for connection attempts
docker compose logs -f fleet-telemetry | grep -i "connect\|vehicle\|tls"

# Check if port 443 accessible from internet
# Use: https://www.yougetsignal.com/tools/open-ports/
# Or from phone hotspot:
nc -zv tesla-telemetry.yourdomain.com 443
```

**Solutions**:

1. **Virtual key not paired**:
   - Open Tesla app → Vehicle → Keys
   - Should show: "Fleet Telemetry Key"
   - If missing, re-pair: https://tesla.com/_ak/tesla-telemetry.yourdomain.com

2. **Telemetry config not sent**:
   ```bash
   # Resend telemetry configuration
   curl -X POST \
     "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/fleet_telemetry_config" \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
     -H "Content-Type: application/json" \
     -d @telemetry_config.json
   ```

3. **Vehicle firmware too old**:
   - Required: 2024.26+ (2023.20.6+ for legacy)
   - Check: Tesla app → Software
   - Update if available

4. **Vehicle has no internet**:
   - Check LTE signal in vehicle
   - Try waking vehicle: Tesla app or API
   - Wait 5-10 minutes for connection

5. **Public key verification failed**:
   ```bash
   # Test public key URL
   curl https://tesla-telemetry.yourdomain.com/.well-known/appspecific/com.tesla.3p.public-key.pem

   # Should return PEM-formatted key
   # If 404, check Nginx config or Fleet Telemetry public key serving
   ```

---

### Telemetry Config Rejected

**Symptoms**:
- API returns error when sending config
- Vehicle receives but doesn't apply config
- No data streaming despite connection

**Diagnosis**:

```bash
# Check API response
curl -X POST \
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/fleet_telemetry_config" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @telemetry_config.json \
  -v

# Check config file syntax
jq . telemetry_config.json
```

**Common Errors**:

1. **Invalid JSON syntax**:
   ```bash
   # Validate and format
   jq . telemetry_config.json > telemetry_config_formatted.json
   mv telemetry_config_formatted.json telemetry_config.json
   ```

2. **Invalid field names**:
   - Check Tesla's telemetry documentation for valid field names
   - Common typo: `Location` (correct) vs `location` (incorrect)

3. **Invalid intervals**:
   - Minimum interval: 1 second
   - Some fields have minimum restrictions
   - Don't use 0 (means disabled)

4. **CA mismatch**:
   ```json
   {
     "ca": "letsencrypt"  // Must match certificate issuer
   }
   ```

5. **Hostname mismatch**:
   ```json
   {
     "hostname": "tesla-telemetry.yourdomain.com"  // Must match server cert CN
   }
   ```

---

### Data Not Streaming (Vehicle Connected)

**Symptoms**:
- Fleet-telemetry shows vehicle connected
- But no messages arriving at MQTT broker
- Or messages arriving but empty

**Diagnosis**:

```bash
# Check fleet-telemetry logs for message processing
docker compose logs fleet-telemetry | grep -i "received\|message\|telemetry\|mqtt"

# Check MQTT for messages
mosquitto_sub -h 192.168.1.50 -u mqtt_user -P mqtt_password -t "tesla/#" -v

# Wait for vehicle to send data (may take a few minutes)
```

**Solutions**:

1. **Telemetry config not applied**:
   - Resend config (see above)
   - Wait 5-10 minutes for vehicle to apply
   - Check vehicle logs in Tesla app (if available)

2. **Vehicle in deep sleep**:
   - Wake vehicle using app
   - Drive vehicle for 1-2 minutes
   - Streaming starts when vehicle is active

3. **Rate limiting enabled**:
   ```json
   // In config.json
   "rate_limit": {
     "enabled": true,
     "message_limit": 1000,  // Increase if needed
     "message_interval_time_seconds": 30
   }
   ```

4. **MQTT QoS issues**:
   ```bash
   # Verify QoS setting in config.json
   grep -A 10 '"mqtt"' config.json

   # QoS 1 (at least once) is recommended for reliability
   ```

---

## Home Assistant Integration Issues

### Integration Won't Load

**Symptoms**:
- HA logs show: `Error loading custom_components.tesla_telemetry_local`
- Integration not listed in Add Integration page
- No entities created

**Diagnosis**:

```bash
# Check HA logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Check file permissions
ls -la /config/custom_components/tesla_telemetry_local/
```

**Solutions**:

1. **Missing files**:
   ```bash
   # Ensure all files are present
   ls -la /config/custom_components/tesla_telemetry_local/

   # Should include: __init__.py, manifest.json, config_flow.py,
   #                 sensor.py, binary_sensor.py, device_tracker.py,
   #                 mqtt_client.py, const.py, strings.json, translations/
   ```

2. **Syntax error in Python files**:
   ```bash
   # Check for syntax errors
   python3 -m py_compile /config/custom_components/tesla_telemetry_local/__init__.py
   python3 -m py_compile /config/custom_components/tesla_telemetry_local/mqtt_client.py
   ```

3. **Missing manifest.json**:
   ```bash
   # Ensure manifest.json exists and is valid
   cat /config/custom_components/tesla_telemetry_local/manifest.json
   ```

4. **HA version incompatible**:
   - Check manifest.json: `"homeassistant": "2024.1.0"`
   - Update HA if too old

5. **MQTT integration not configured**:
   - Go to Settings → Devices & Services
   - Ensure MQTT integration is set up and connected to Mosquitto

---

### Integration Not Found in Add Integration

**Symptoms**:
- "Tesla Fleet Telemetry Local" doesn't appear when searching

**Solutions**:

1. **Files not copied correctly**:
   ```bash
   # Verify directory structure
   ls -la /config/custom_components/tesla_telemetry_local/

   # Should show all .py files
   ```

2. **Restart Home Assistant**:
   ```bash
   ha core restart
   ```

3. **Check HA logs for import errors**:
   ```bash
   grep -i "tesla_telemetry_local" /config/home-assistant.log | head -20
   ```

4. **Clear browser cache**:
   - Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
   - Try incognito/private window

---

### Entities Not Updating

**Symptoms**:
- Entities exist but show "Unknown" or old values
- No state changes in Developer Tools
- Logbook shows no updates

**Diagnosis**:

```bash
# Check MQTT messages are arriving
mosquitto_sub -h localhost -t "tesla/#" -v

# Check integration logs with debug
# Add to configuration.yaml:
# logger:
#   logs:
#     custom_components.tesla_telemetry_local: debug

# Restart HA and check logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local
```

**Solutions**:

1. **MQTT not connected**:
   - Check MQTT integration status in HA
   - Settings → Devices & Services → MQTT → should show "Connected"

2. **Wrong topic base**:
   - Check integration configuration matches server config
   - Topic base should be `tesla` (or whatever configured in server)

3. **VIN mismatch**:
   - Check VIN in integration matches vehicle sending data
   - VINs are case-sensitive

4. **No messages from vehicle**:
   ```bash
   # Monitor MQTT directly
   mosquitto_sub -h localhost -t "tesla/#" -v

   # If no messages, check fleet-telemetry server
   # Wake vehicle and wait 5-10 minutes
   ```

---

### High Latency

**Symptoms**:
- Entity updates delayed 10-60+ seconds
- Real-time events missed (garage door doesn't open)
- Dashboard slow to refresh

**Diagnosis**:

```bash
# Measure round-trip time
# 1. Start timer when vehicle event (shift to D)
# 2. Check HA entity update time
# 3. Calculate difference

# Check HA system load
docker exec -it homeassistant top
```

**Solutions**:

1. **MQTT QoS too low**:
   - QoS 0: No guarantee (fastest but unreliable)
   - QoS 1: At least once (recommended)
   - QoS 2: Exactly once (slowest)

2. **HA overloaded**:
   - Increase Docker container resources (CPU/RAM)
   - Disable unnecessary integrations
   - Reduce polling intervals for other integrations

3. **Network latency**:
   ```bash
   # Test latency
   ping -c 10 192.168.1.50

   # Should be <1ms on LAN
   # If higher, check network issues
   ```

4. **Vehicle telemetry intervals too long**:
   - Check telemetry_config.json field intervals
   - Reduce `interval_seconds` for critical fields

---

## OAuth Token Issues

### Access Token Expired

**Symptoms**:
- API returns: `401 Unauthorized`
- Cannot send telemetry config
- Cannot send vehicle commands

**Solutions**:

```bash
# Refresh token manually
cd /opt/tesla-telemetry/server
./scripts/refresh_token.sh

# Check token expiry
jq '.expires_at' tesla_tokens.json
date -d @$(jq -r '.expires_at' tesla_tokens.json)

# If expired, run refresh script
```

### Automatic Refresh Not Working

**Symptoms**:
- Tokens expire despite cron job
- No logs in token_refresh.log

**Diagnosis**:

```bash
# Check cron job exists
crontab -l | grep refresh_token

# Check script is executable
ls -la /opt/tesla-telemetry/server/scripts/refresh_token.sh

# Run manually to test
./scripts/refresh_token.sh
```

**Solutions**:

1. **Cron not running**:
   ```bash
   systemctl status cron
   systemctl start cron
   ```

2. **Script has errors**:
   ```bash
   # Run manually to see errors
   bash -x ./scripts/refresh_token.sh
   ```

3. **Wrong permissions**:
   ```bash
   chmod +x ./scripts/refresh_token.sh
   chown root:root ./scripts/refresh_token.sh
   ```

---

## Performance Issues

### High CPU Usage

**Symptoms**:
- Docker containers use 80-100% CPU
- Server becomes unresponsive

**Diagnosis**:

```bash
# Check container CPU usage
docker stats

# Check which process
docker exec -it fleet-telemetry top
```

**Solutions**:

1. **Too many messages**:
   - Reduce telemetry intervals in vehicle config
   - Increase `interval_seconds` for less critical fields

2. **Fleet-telemetry parsing issues**:
   - Check for JSON parsing errors
   - Reduce log level from debug to info

3. **Insufficient resources**:
   - Increase container CPU allocation
   - Increase RAM allocation

---

### High Memory Usage

**Symptoms**:
- Out of memory errors
- Containers restarting
- System becomes slow

**Diagnosis**:

```bash
# Check memory usage
free -h
docker stats
```

**Solutions**:

1. **Reduce message retention**:
   - MQTT doesn't retain all messages by default
   - Check `retained` setting in config.json

2. **Increase container memory**:
   ```bash
   # Increase Docker container memory limit
   # In docker-compose.yml:
   deploy:
     resources:
       limits:
         memory: 1G
   ```

3. **Restart periodically**:
   - If memory leaks, schedule periodic restarts
   - Use healthcheck with restart policy

---

## Getting Help

### Collect Debug Information

Before asking for help, collect this information:

```bash
# System info
uname -a
docker --version
docker compose version

# Service status
docker compose ps
docker compose logs --tail=100 > debug_logs.txt

# MQTT connectivity test
mosquitto_sub -h YOUR_MQTT_BROKER -t "tesla/#" -v -C 5 > mqtt_messages.txt

# Certificate info
./scripts/validate_cert.sh tesla-telemetry.yourdomain.com > cert_validation.txt

# Configuration (REDACT SECRETS!)
cat config.json | jq 'del(.mqtt.password) | del(.tls.server_key)' > config_sanitized.json
```

### Where to Get Help

1. **GitHub Issues**: https://github.com/jjtortosa/seitor-tesla-telemetry/issues
2. **Home Assistant Community**: https://community.home-assistant.io/
3. **Tesla Fleet API Docs**: https://developer.tesla.com/docs/fleet-api

### Create a Good Bug Report

Include:
- System info (OS, Docker version, HA version)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (redact secrets!)
- Configuration (redact secrets!)

---

## Common Quick Fixes

### "It stopped working suddenly"

**Try in order**:

1. Restart Docker stack:
   ```bash
   docker compose restart
   ```

2. Refresh Tesla token:
   ```bash
   ./scripts/refresh_token.sh
   ```

3. Wake vehicle:
   - Open Tesla app
   - Wait for vehicle to wake
   - Drive for 1-2 minutes

4. Check certificate expiry:
   ```bash
   ./scripts/validate_cert.sh tesla-telemetry.yourdomain.com
   ```

5. Check public IP hasn't changed (if using DDNS):
   ```bash
   curl ifconfig.me
   # Compare with DNS: nslookup tesla-telemetry.yourdomain.com
   ```

6. Check MQTT broker is running:
   ```bash
   # In Home Assistant
   # Settings → Add-ons → Mosquitto broker → Check status
   ```

7. Full system restart:
   ```bash
   docker compose down
   docker compose up -d
   ha core restart  # On Home Assistant
   ```

---

**Still having issues?** Check the [GitHub Issues](https://github.com/jjtortosa/seitor-tesla-telemetry/issues) or create a new one with debug information.
