# Tesla Fleet Telemetry - Testing Checklist

Quick checklist for real-world testing.

## Pre-Testing Setup

### Information Gathering
- [ ] Tesla VIN: `_____________________`
- [ ] Home Assistant IP: `_____________________`
- [ ] Domain configured: `tesla-telemetry.seitor.com`
- [ ] SSL certificate ready
- [ ] Tesla Developer setup complete (keys, virtual key)
- [ ] MQTT broker configured in HA

### Access Verification
- [ ] Can access Home Assistant UI
- [ ] Can access Home Assistant logs
- [ ] MQTT broker running

---

## Phase 1: Server Deployment

### Deploy Fleet Telemetry Stack
- [ ] Clone repository
- [ ] SSL certificates in place
- [ ] Review `config.json` (correct hostname, MQTT settings)
- [ ] Run `docker-compose up -d`
- [ ] Verify containers running: `docker-compose ps`

### Verify Services
- [ ] HTTPS endpoint working: `curl https://tesla-telemetry.seitor.com/status`
- [ ] Fleet Telemetry logs show "Server started"
- [ ] MQTT broker accessible

**Estimated time**: 1-2 hours

---

## Phase 2: HA Integration

### Install Integration
- [ ] Copy integration to `/config/custom_components/tesla_telemetry_local/`
- [ ] Restart Home Assistant
- [ ] Integration appears in Settings > Integrations

### Configure via UI
- [ ] Add integration: Settings > Integrations > Add Integration
- [ ] Search "Tesla Fleet Telemetry Local"
- [ ] Enter MQTT topic base: `tesla`
- [ ] Enter vehicle VIN
- [ ] Enter vehicle name
- [ ] Enable debug logging in configuration.yaml

### Verify Loading
- [ ] Check logs: `grep tesla_telemetry_local home-assistant.log`
- [ ] See "Setting up Tesla Fleet Telemetry Local integration"
- [ ] See "Tesla MQTT client started successfully"

**Estimated time**: 30 minutes

---

## Phase 3: First Messages

### Trigger Vehicle
- [ ] Get in Tesla
- [ ] Wake up vehicle (climate control, or phone app)
- [ ] Wait 1-2 minutes for telemetry to start

### Monitor MQTT
- [ ] Subscribe to topics: `mosquitto_sub -t "tesla/#" -v`
- [ ] See messages appearing
- [ ] Verify VIN matches your vehicle
- [ ] See fields: Location, VehicleSpeed, Gear, Soc, etc.

### Monitor HA
- [ ] Check HA logs for tesla_telemetry_local
- [ ] See "Received telemetry" messages
- [ ] See field parsing (Location, Speed, Battery, etc.)
- [ ] No parse errors

**Estimated time**: 30 minutes

---

## Phase 4: Entity Verification

### Check Entities Exist
- [ ] Go to Settings > Devices & Services
- [ ] Find "Tesla Fleet Telemetry Local"
- [ ] Count entities: Should be 13 total
  - 1 device_tracker
  - 8 sensors
  - 4 binary_sensors

### Verify Device Tracker
- [ ] `device_tracker.VEHICLENAME_location`
- [ ] Has latitude/longitude
- [ ] Shows on HA map
- [ ] Updates when vehicle moves

### Verify Sensors
- [ ] `sensor.VEHICLENAME_speed` (km/h, changes when driving)
- [ ] `sensor.VEHICLENAME_shift_state` (P/D/R/N)
- [ ] `sensor.VEHICLENAME_battery` (%, matches vehicle display)
- [ ] `sensor.VEHICLENAME_range` (km, estimated range)
- [ ] `sensor.VEHICLENAME_charging_state`
- [ ] `sensor.VEHICLENAME_charger_voltage` (V, when charging)
- [ ] `sensor.VEHICLENAME_charger_current` (A, when charging)
- [ ] `sensor.VEHICLENAME_odometer` (km)

### Verify Binary Sensors
- [ ] `binary_sensor.VEHICLENAME_driving` (on when moving)
- [ ] `binary_sensor.VEHICLENAME_charging` (on when plugged in)
- [ ] `binary_sensor.VEHICLENAME_charge_port_open`
- [ ] `binary_sensor.VEHICLENAME_connected` (vehicle awake)

**Estimated time**: 30 minutes

---

## Phase 5: Scenario Testing

### Scenario 1: Parked
**Action**: Vehicle parked, locked, not charging

- [ ] `sensor.VEHICLENAME_speed` = 0
- [ ] `sensor.VEHICLENAME_shift_state` = P
- [ ] `binary_sensor.VEHICLENAME_driving` = off
- [ ] `binary_sensor.VEHICLENAME_charging` = off
- [ ] Location stable

### Scenario 2: Driving
**Action**: Start driving

- [ ] `sensor.VEHICLENAME_speed` matches dashboard
- [ ] `sensor.VEHICLENAME_shift_state` = D
- [ ] `binary_sensor.VEHICLENAME_driving` = on
- [ ] `device_tracker.VEHICLENAME_location` updates every ~5-10 sec
- [ ] Latency <5 seconds

**Time actual latency**: _____ seconds

### Scenario 3: Charging
**Action**: Plug in charger

- [ ] `binary_sensor.VEHICLENAME_charging` = on
- [ ] `sensor.VEHICLENAME_charging_state` = Charging
- [ ] `sensor.VEHICLENAME_charger_voltage` shows voltage
- [ ] `sensor.VEHICLENAME_charger_current` shows amperage
- [ ] Battery level increases over time

### Scenario 4: Zones
**Action**: Drive to work/store/etc.

- [ ] `device_tracker.VEHICLENAME_location` state changes to zone name
- [ ] Zone transitions recorded in history
- [ ] Zone enter/exit events work

**Estimated time**: 2-3 hours (requires driving)

---

## Phase 6: Automations

### Test Automation 1: Arrival Notification
- [ ] Create automation in UI
- [ ] Drive away from home
- [ ] Drive back home
- [ ] Notification appears

### Test Automation 2: Charging Notification
- [ ] Create automation
- [ ] Unplug charger
- [ ] Plug in charger
- [ ] Notification appears

### Test Automation 3: Low Battery Alert
- [ ] Create automation (threshold: 20%)
- [ ] Wait for battery to drop below 20% (or adjust threshold)
- [ ] Notification appears when not charging

**Estimated time**: 1 hour

---

## Phase 7: Stability Testing

### 24-Hour Soak Test
- [ ] Leave system running for 24 hours
- [ ] Monitor logs for errors
- [ ] Check no memory leaks
- [ ] No disconnections or crashes

### Resource Usage
- [ ] HA memory usage: _______ MB (stable?)
- [ ] CPU usage: _______ % (acceptable?)

**Estimated time**: 24 hours passive monitoring

---

## Success Criteria

Mark complete when ALL are true:

- [ ] MQTT receives messages from Fleet Telemetry
- [ ] All entities created and updating
- [ ] Latency measured: _____ seconds (<5s goal)
- [ ] All 4 scenarios tested successfully
- [ ] Automations trigger correctly
- [ ] System stable for 24+ hours
- [ ] No memory leaks or crashes
- [ ] Resource usage acceptable

---

## Troubleshooting Quick Reference

### No messages in MQTT
```bash
# Check Fleet Telemetry logs
docker logs -f fleet-telemetry

# Subscribe to MQTT
mosquitto_sub -h localhost -t "tesla/#" -v

# Check Tesla app shows "Data Sharing" enabled
```

### HA Integration not loading
```bash
# Check logs
tail -f /config/home-assistant.log | grep ERROR

# Check integration status in UI
# Settings > Integrations > Tesla Fleet Telemetry Local
```

### Entities not updating
1. Check MQTT messages are arriving
2. Verify HA logs show message processing
3. Check topic base matches configuration
4. Restart Home Assistant

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
