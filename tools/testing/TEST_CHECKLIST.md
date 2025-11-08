# Tesla Fleet Telemetry - Testing Checklist

Quick checklist for real-world testing on HA Test instance.

## Pre-Testing Setup

### Information Gathering
- [ ] Tesla VIN: `_____________________`
- [ ] HA Test IP: `_____________________`
- [ ] Domain configured: `tesla-telemetry.seitor.com`
- [ ] SSL certificate ready or will use Let's Encrypt
- [ ] Tesla Developer setup complete (keys, virtual key)

### Access Verification
- [ ] Can SSH/console into HA Test container
- [ ] Docker installed and working: `docker --version`
- [ ] Git installed: `git --version`
- [ ] Ports 9092 and 443 available

---

## Phase 1: Server Deployment

### Deploy Stack
- [ ] Clone repository to `/opt/seitor-tesla-telemetry`
- [ ] SSL certificates in `server/certs/`
- [ ] Review `server/config.json` (correct hostname)
- [ ] Run `docker-compose up -d` in `server/`
- [ ] Verify containers running: `docker-compose ps`

### Verify Services
- [ ] Kafka listening on 9092: `netstat -tuln | grep 9092`
- [ ] HTTPS endpoint working: `curl https://tesla-telemetry.seitor.com/status`
- [ ] Fleet Telemetry logs show "Server started"
- [ ] Can connect to Kafka: `nc -zv localhost 9092`

**Estimated time**: 1-2 hours
**Blocker**: Cannot proceed without working Kafka

---

## Phase 2: HA Integration

### Install Integration
- [ ] Access HA container: `docker exec -it homeassistant bash`
- [ ] Copy integration to `/config/custom_components/tesla_telemetry_local/`
- [ ] Install dependencies: `pip3 install kafka-python==2.0.2 protobuf>=5.27.0`
- [ ] Verify: `pip3 list | grep -E "kafka|protobuf"`

### Configure
- [ ] Edit `/config/configuration.yaml`
- [ ] Add tesla_telemetry_local config with:
  - kafka_broker: `localhost:9092`
  - vehicle_vin: `YOUR_VIN`
  - vehicle_name: `MelanY`
- [ ] Enable debug logging
- [ ] Restart HA: `ha core restart`

### Verify Loading
- [ ] Wait 30 seconds for restart
- [ ] Check logs: `tail -f /config/home-assistant.log | grep tesla_telemetry_local`
- [ ] See "Setting up tesla_telemetry_local"
- [ ] See "Successfully connected to Kafka broker"

**Estimated time**: 30 minutes
**Blocker**: Cannot proceed without HA loading integration

---

## Phase 3: First Messages

### Trigger Vehicle
- [ ] Get in Tesla
- [ ] Wake up vehicle (climate control, or phone app)
- [ ] Wait 1-2 minutes for telemetry to start

### Monitor Kafka
- [ ] Terminal 1: Run `tools/testing/kafka_debugger.py --broker localhost:9092`
- [ ] See messages appearing
- [ ] Verify VIN matches your vehicle
- [ ] See fields: Location, VehicleSpeed, Gear, Soc, etc.

### Monitor HA
- [ ] Terminal 2: `tail -f /config/home-assistant.log | grep tesla_telemetry_local`
- [ ] See "Received telemetry message"
- [ ] See field parsing (Location, Speed, Battery, etc.)
- [ ] No parse errors

**Estimated time**: 30 minutes
**Blocker**: Cannot proceed without messages

---

## Phase 4: Entity Verification

### Check Entities Exist
- [ ] Run: `ha state list | grep melany`
- [ ] Count entities: Should be 13 total
  - 1 device_tracker
  - 8 sensors
  - 4 binary_sensors

### Verify Device Tracker
- [ ] `ha state get device_tracker.melany_location`
- [ ] Has latitude/longitude
- [ ] Shows on HA map
- [ ] Updates when vehicle moves

### Verify Sensors
- [ ] `sensor.melany_speed` (km/h, changes when driving)
- [ ] `sensor.melany_shift_state` (P/D/R/N)
- [ ] `sensor.melany_battery` (%, matches vehicle display)
- [ ] `sensor.melany_range` (km, estimated range)
- [ ] `sensor.melany_charging_state`
- [ ] `sensor.melany_charger_voltage` (V, when charging)
- [ ] `sensor.melany_charger_current` (A, when charging)
- [ ] `sensor.melany_odometer` (km)

### Verify Binary Sensors
- [ ] `binary_sensor.melany_driving` (on when moving)
- [ ] `binary_sensor.melany_charging` (on when plugged in)
- [ ] `binary_sensor.melany_charge_port_open`
- [ ] `binary_sensor.melany_connected` (vehicle awake)

**Estimated time**: 30 minutes

---

## Phase 5: Scenario Testing

### Scenario 1: Parked
**Action**: Vehicle parked, locked, not charging

- [ ] `sensor.melany_speed` = 0
- [ ] `sensor.melany_shift_state` = P
- [ ] `binary_sensor.melany_driving` = off
- [ ] `binary_sensor.melany_charging` = off
- [ ] Location stable

### Scenario 2: Driving
**Action**: Start driving

- [ ] `sensor.melany_speed` matches dashboard
- [ ] `sensor.melany_shift_state` = D
- [ ] `binary_sensor.melany_driving` = on
- [ ] `device_tracker.melany_location` updates every ~5-10 sec
- [ ] Latency <5 seconds

**Time actual latency**: _____ seconds

### Scenario 3: Charging
**Action**: Plug in charger

- [ ] `binary_sensor.melany_charging` = on
- [ ] `sensor.melany_charging_state` = Charging
- [ ] `sensor.melany_charger_voltage` shows voltage
- [ ] `sensor.melany_charger_current` shows amperage
- [ ] Battery level increases over time

### Scenario 4: Zones
**Action**: Drive to work/store/etc.

- [ ] `device_tracker.melany_location` state changes to zone name
- [ ] Zone transitions recorded in history
- [ ] Zone enter/exit events work

**Estimated time**: 2-3 hours (requires driving)

---

## Phase 6: Automations

### Test Automation 1: Arrival Notification
- [ ] Create automation in configuration.yaml
- [ ] Drive away from home
- [ ] Drive back home
- [ ] Notification appears: "MelanY has arrived"

### Test Automation 2: Charging Notification
- [ ] Create automation
- [ ] Unplug charger
- [ ] Plug in charger
- [ ] Notification appears: "MelanY started charging at X%"

### Test Automation 3: Low Battery Alert
- [ ] Create automation (threshold: 20%)
- [ ] Wait for battery to drop below 20% (or adjust threshold)
- [ ] Notification appears when not charging

**Estimated time**: 1 hour

---

## Phase 7: Stability Testing

### 24-Hour Soak Test
- [ ] Leave system running for 24 hours
- [ ] Monitor logs for errors: `tail -f /config/home-assistant.log`
- [ ] Check Docker stats: `docker stats` (no memory leaks)
- [ ] Verify Kafka consumer lag stays low
- [ ] No disconnections or crashes

### Resource Usage
- [ ] HA container memory: _______ MB (stable?)
- [ ] Kafka container memory: _______ MB (stable?)
- [ ] CPU usage: _______ % (acceptable?)

**Estimated time**: 24 hours passive monitoring

---

## Success Criteria

Mark complete when ALL are true:

- [ ] ✅ Kafka receives messages from Tesla
- [ ] ✅ Protobuf parsing works (no errors in logs)
- [ ] ✅ All 13 entities created and updating
- [ ] ✅ Latency measured: _____ seconds (<5s goal)
- [ ] ✅ All 4 scenarios tested successfully
- [ ] ✅ Automations trigger correctly
- [ ] ✅ System stable for 24+ hours
- [ ] ✅ No memory leaks or crashes
- [ ] ✅ Resource usage acceptable

---

## Troubleshooting Quick Reference

### No messages in Kafka
```bash
# Check Fleet Telemetry logs
docker logs -f fleet-telemetry

# Check if vehicle is paired correctly
# Check Tesla app shows "Data Sharing" enabled

# Verify Kafka is working
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092
```

### HA Integration not loading
```bash
# Check logs
tail -f /config/home-assistant.log | grep ERROR

# Verify dependencies
docker exec -it homeassistant pip3 list | grep -E "kafka|protobuf"

# Check configuration syntax
docker exec -it homeassistant python3 -m homeassistant --script check_config
```

### Parse errors
```bash
# Check Protobuf version
docker exec -it homeassistant pip3 show protobuf
# Must be >=5.27.0

# Update if needed
docker exec -it homeassistant pip3 install --upgrade protobuf

# Restart HA
ha core restart
```

### High latency
```bash
# Check network
docker exec -it homeassistant ping localhost

# Check Kafka consumer lag
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group ha_tesla_YOUR_VIN \
  --describe
```

---

## Migration to Ubuntu Server (If Needed)

**When to migrate**:
- HA Test struggles with resources
- Want to separate concerns
- Need more scalability

**How** (Quick):
1. Deploy stack on Ubuntu Server
2. Change HA config: `kafka_broker: "UBUNTU_IP:9092"`
3. Restart HA
4. Stop services on HA Test

See `docs/07_real_world_testing.md` for details.

---

## Notes

### Issues Encountered


### Actual Latency Measurements


### Useful Fields Discovered


### Ideas for Future Automations


---

**Date Started**: _______________
**Date Completed**: _______________
**Total Time**: _______________
