# Troubleshooting Guide

Comprehensive troubleshooting guide for Tesla Fleet Telemetry self-hosted system.

## Quick Diagnostics

### System Health Check

Run this command on your Proxmox container to get overall system status:

```bash
cd /opt/tesla-telemetry/server

# Check all services
docker compose ps

# Check logs for errors
docker compose logs --tail=100 | grep -i error

# Test Kafka
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Test certificate
./scripts/validate_cert.sh tesla-telemetry.seitor.com

# Check fleet-telemetry health
curl http://localhost:8443/health
```

**Healthy system output**:
- All containers: `Up` + `healthy`
- No ERROR messages in logs
- Kafka topics listed successfully
- Certificate validation passes
- Health endpoint returns: `OK`

---

## Infrastructure Issues

### DNS Not Resolving

**Symptoms**:
- `nslookup tesla-telemetry.seitor.com` fails
- Cannot access domain from browser
- Certificate validation fails with DNS error

**Diagnosis**:

```bash
# Test DNS resolution
nslookup tesla-telemetry.seitor.com

# Test from different DNS server
nslookup tesla-telemetry.seitor.com 8.8.8.8

# Check DNS propagation
dig tesla-telemetry.seitor.com +trace
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
- `nc -zv tesla-telemetry.seitor.com 443` fails from outside network
- Certificate validation fails on connectivity
- Vehicle cannot connect

**Diagnosis**:

```bash
# Test from server (should work)
nc -zv localhost 443

# Test from LAN (should work)
nc -zv 192.168.5.105 443

# Test from outside (use phone hotspot or https://www.yougetsignal.com/tools/open-ports/)
nc -zv tesla-telemetry.seitor.com 443
```

**Solutions**:

1. **Check port forwarding on router**:
   - Rule: WAN 443 → LAN 192.168.5.105:443
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
./scripts/validate_cert.sh tesla-telemetry.seitor.com

# Check certificate details
openssl s_client -connect tesla-telemetry.seitor.com:443 -servername tesla-telemetry.seitor.com

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
   cp /etc/letsencrypt/live/tesla-telemetry.seitor.com/*.pem certs/
   ```

3. **Port already in use**:
   ```bash
   # Check if something else uses port 443
   netstat -tulpn | grep 443

   # Kill process or change port
   ```

4. **Kafka not ready**:
   ```bash
   # Check Kafka is healthy first
   docker compose ps kafka

   # If unhealthy, check Kafka logs
   docker compose logs kafka
   ```

---

### Kafka Connection Issues

**Symptoms**:
- Fleet-telemetry logs: `Kafka connection failed`
- No messages in Kafka topic
- Kafka UI shows no topics

**Diagnosis**:

```bash
# Check Kafka is running
docker compose ps kafka

# Check Kafka logs
docker compose logs kafka | tail -50

# Test Kafka from inside container
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Test Kafka from fleet-telemetry
docker compose exec fleet-telemetry sh
nc -zv kafka 9092
```

**Solutions**:

1. **Kafka not started**:
   ```bash
   docker compose restart kafka
   docker compose logs -f kafka
   ```

2. **Zookeeper issues**:
   ```bash
   # Kafka depends on Zookeeper
   docker compose restart zookeeper
   docker compose restart kafka
   ```

3. **Network issues**:
   ```bash
   # Check Docker network
   docker network ls
   docker network inspect server_tesla-net

   # Recreate network
   docker compose down
   docker compose up -d
   ```

4. **Kafka disk space full**:
   ```bash
   # Check volume usage
   docker system df -v

   # Clean old data
   docker compose down
   docker volume rm server_kafka-data
   docker compose up -d
   ```

---

## Tesla Vehicle Issues

### Vehicle Not Connecting

**Symptoms**:
- No connection logs in fleet-telemetry
- No messages in Kafka
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
nc -zv tesla-telemetry.seitor.com 443
```

**Solutions**:

1. **Virtual key not paired**:
   - Open Tesla app → Vehicle → Keys
   - Should show: "Fleet Telemetry Key"
   - If missing, re-pair: https://tesla.com/_ak/tesla-telemetry.seitor.com

2. **Telemetry config not sent**:
   ```bash
   # Resend telemetry configuration
   curl -X POST \
     "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/command/fleet_telemetry_config" \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
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
   curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem

   # Should return PEM-formatted key
   # If 404, check Nginx config
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
  "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/${VEHICLE_ID}/command/fleet_telemetry_config" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
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
   - Check Tesla's Protobuf schema for valid field names
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
     "hostname": "tesla-telemetry.seitor.com"  // Must match server cert CN
   }
   ```

---

### Data Not Streaming (Vehicle Connected)

**Symptoms**:
- Fleet-telemetry shows vehicle connected
- But no messages arriving in Kafka
- Or messages arriving but empty

**Diagnosis**:

```bash
# Check fleet-telemetry logs for message processing
docker compose logs fleet-telemetry | grep -i "received\|message\|telemetry"

# Check Kafka for messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --max-messages 10

# Check Kafka UI
# Open: http://192.168.5.105:8080
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

4. **Kafka topic full**:
   ```bash
   # Check Kafka disk usage
   docker exec -it kafka df -h /var/lib/kafka/data

   # Increase retention or clean old data
   ```

---

## Home Assistant Integration Issues

### Integration Won't Load

**Symptoms**:
- HA logs show: `Error loading custom_components.tesla_telemetry_local`
- Integration not listed in Integrations page
- No entities created

**Diagnosis**:

```bash
# Check HA logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Check Python dependencies
docker exec -it homeassistant python3 -c "import kafka; import google.protobuf"

# Check file permissions
ls -la /config/custom_components/tesla_telemetry_local/
```

**Solutions**:

1. **Missing dependencies**:
   ```bash
   # Install in HA container
   docker exec -it homeassistant pip3 install kafka-python==2.0.2 protobuf==4.25.1

   # Restart HA
   ha core restart
   ```

2. **Syntax error in Python files**:
   ```bash
   # Check for syntax errors
   python3 -m py_compile /config/custom_components/tesla_telemetry_local/__init__.py
   ```

3. **Missing manifest.json**:
   ```bash
   # Ensure manifest.json exists and is valid
   cat /config/custom_components/tesla_telemetry_local/manifest.json
   ```

4. **HA version incompatible**:
   - Check manifest.json: `"homeassistant": "2024.1.0"`
   - Update HA if too old

---

### Entities Not Updating

**Symptoms**:
- Entities exist but show "Unknown" or old values
- No state changes in Developer Tools
- Logbook shows no updates

**Diagnosis**:

```bash
# Check Kafka connectivity from HA
docker exec -it homeassistant nc -zv 192.168.5.105 9092

# Check integration logs
tail -f /config/home-assistant.log | grep tesla_telemetry_local

# Enable debug logging
# Add to configuration.yaml:
# logger:
#   logs:
#     custom_components.tesla_telemetry_local: debug
```

**Solutions**:

1. **Kafka unreachable**:
   ```bash
   # Check firewall allows port 9092
   # On Proxmox container:
   ufw allow 9092/tcp

   # Or disable firewall temporarily to test
   ufw disable
   ```

2. **Wrong Kafka broker IP**:
   ```yaml
   # In configuration.yaml
   tesla_telemetry_local:
     kafka_broker: "192.168.5.105:9092"  # Must be container IP
   ```

3. **Protobuf parsing fails**:
   ```bash
   # Check logs for decode errors
   grep -i "protobuf\|decode" /config/home-assistant.log

   # Recompile Protobuf if needed
   protoc --python_out=. vehicle_data.proto
   ```

4. **Consumer lag**:
   - Check Kafka UI: Topics → tesla_telemetry → Consumer Groups
   - Look for lag (messages not consumed)
   - Restart HA to reset consumer

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

# Check Kafka UI for consumer lag

# Check HA system load
docker exec -it homeassistant top
```

**Solutions**:

1. **Kafka consumer lag**:
   - Check Kafka UI → Consumer Groups
   - Increase `max_poll_records` in integration config
   - Add more consumer threads

2. **HA overloaded**:
   - Increase Docker container resources (CPU/RAM)
   - Disable unnecessary integrations
   - Reduce polling intervals for other integrations

3. **Network latency**:
   ```bash
   # Test latency
   ping -c 10 192.168.5.105

   # Should be <1ms on LAN
   # If higher, check network issues
   ```

4. **Protobuf parsing slow**:
   - Profile parsing time
   - Consider caching parsed messages
   - Use compiled Protobuf (not pure Python)

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
- Kafka lag increases

**Diagnosis**:

```bash
# Check container CPU usage
docker stats

# Check which process
docker exec -it <container> top
```

**Solutions**:

1. **Kafka processing too many messages**:
   - Reduce telemetry intervals in vehicle config
   - Increase retention (delete old messages)

2. **Fleet-telemetry parsing issues**:
   - Check for Protobuf decode errors
   - Reduce log level from debug to info

3. **Insufficient resources**:
   - Increase Proxmox container CPU allocation
   - Increase RAM allocation

---

### High Memory Usage

**Symptoms**:
- Out of memory errors
- Containers restarting
- Kafka becomes slow

**Diagnosis**:

```bash
# Check memory usage
free -h
docker stats

# Check Kafka memory
docker exec -it kafka java -XshowSettings:vm -version
```

**Solutions**:

1. **Kafka buffer too large**:
   ```yaml
   # In docker-compose.yml, add:
   environment:
     KAFKA_HEAP_OPTS: "-Xmx512M -Xms512M"
   ```

2. **Too many messages retained**:
   ```bash
   # Reduce retention hours
   # In docker-compose.yml:
   KAFKA_LOG_RETENTION_HOURS: 24  # Instead of 168
   ```

3. **Increase container memory**:
   ```bash
   # In Proxmox: CT → Resources → Memory → Increase to 8GB
   ```

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

# Kafka status
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092 > kafka_topics.txt

# Certificate info
./scripts/validate_cert.sh tesla-telemetry.seitor.com > cert_validation.txt

# Configuration (REDACT SECRETS!)
cat config.json | jq 'del(.tls.server_key)' > config_sanitized.json
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
   ./scripts/validate_cert.sh tesla-telemetry.seitor.com
   ```

5. Check public IP hasn't changed (if using DDNS):
   ```bash
   curl ifconfig.me
   # Compare with DNS: nslookup tesla-telemetry.seitor.com
   ```

6. Full system restart:
   ```bash
   docker compose down
   docker compose up -d
   ha core restart  # On Home Assistant
   ```

---

**Still having issues?** Check the [GitHub Issues](https://github.com/jjtortosa/seitor-tesla-telemetry/issues) or create a new one with debug information.
