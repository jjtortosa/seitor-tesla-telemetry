# QA Checklist: Config Flow Integration

**Date**: 2025-12-13
**Tester**: Claude Code + @juanjo
**HA Version**: 2025.12.3
**Integration Version**: 1.0.0

---

## Prerequisites

### Environment
- [ ] HA Test accessible (192.168.6.41)
- [ ] SSH access working: `ssh root@192.168.6.41`
- [ ] Docker running on HA Test

### Kafka Setup (for connection testing)
```bash
# Option A: Start Kafka on HA Test
cd /opt/seitor-tesla-telemetry/server
docker compose up -d kafka zookeeper

# Option B: Use mock Kafka (just for Config Flow test)
# The Config Flow will fail connection test but we can verify UI works
```

---

## Phase 1: Installation

### 1.1 Copy Integration Files
```bash
# From your Mac
scp -r ha-integration/custom_components/tesla_telemetry_local root@192.168.6.41:/config/custom_components/
```

- [ ] Files copied successfully
- [ ] Verify structure:
```bash
ssh root@192.168.6.41 "ls -la /config/custom_components/tesla_telemetry_local/"
```

Expected files:
```
__init__.py
binary_sensor.py
config_flow.py      ← NEW
const.py            ← NEW
device_tracker.py
diagnostics.py      ← NEW
kafka_consumer.py
manifest.json
sensor.py
strings.json        ← NEW
translations/       ← NEW
vehicle_data_pb2.py
```

### 1.2 Install Dependencies
```bash
ssh root@192.168.6.41 "docker exec -it homeassistant pip3 install kafka-python==2.0.2"
```

- [ ] kafka-python installed

### 1.3 Restart Home Assistant
```bash
ssh root@192.168.6.41 "docker restart homeassistant"
```

- [ ] HA restarted successfully
- [ ] HA accessible via web UI

---

## Phase 2: Config Flow UI Testing

### 2.1 Access Integration Setup
1. Go to: **Settings → Devices & Services → Add Integration**
2. Search for: "Tesla Fleet Telemetry"

- [ ] Integration appears in search results
- [ ] Icon/name displays correctly

### 2.2 Step 1: Kafka Configuration
Fill in the form:
- **Kafka Broker**: `localhost:9092` (or real IP)
- **Kafka Topic**: `tesla_telemetry`

Test scenarios:

| Test | Input | Expected Result | Pass? |
|------|-------|-----------------|-------|
| Valid broker format | `192.168.6.41:9092` | Proceeds to next step | [ ] |
| Invalid broker (no port) | `192.168.6.41` | Error: "Invalid broker format" | [ ] |
| Empty broker | ` ` | Error: Required field | [ ] |
| Connection test fail | `192.168.99.99:9092` | Error: "Cannot connect to Kafka" | [ ] |
| Empty topic | ` ` | Error: Required field | [ ] |

### 2.3 Step 2: Vehicle Configuration
Fill in the form:
- **Vehicle VIN**: `LRWYGCFS3RC210528`
- **Vehicle Name**: `MelanY`

Test scenarios:

| Test | Input | Expected Result | Pass? |
|------|-------|-----------------|-------|
| Valid VIN (17 chars) | `LRWYGCFS3RC210528` | Proceeds to finish | [ ] |
| Short VIN | `LRWYGCFS3RC` | Error: "VIN must be 17 characters" | [ ] |
| Long VIN | `LRWYGCFS3RC2105281234` | Error: "VIN must be 17 characters" | [ ] |
| Empty VIN | ` ` | Error: Required field | [ ] |
| Invalid chars | `LRWYGCFS3RC21052!` | Error: "Invalid VIN format" | [ ] |
| Empty name | ` ` | Uses VIN as name | [ ] |

### 2.4 Completion
- [ ] Integration created successfully
- [ ] Redirects to integration page
- [ ] Shows device with correct name

---

## Phase 3: Entity Verification

### 3.1 Device Created
Go to: **Settings → Devices & Services → Tesla Fleet Telemetry Local**

- [ ] Device appears with name "MelanY"
- [ ] Device shows manufacturer: "Tesla"
- [ ] Device shows VIN in identifiers

### 3.2 Entities Created
Check all entities exist:

**Device Tracker (1)**
- [ ] `device_tracker.melany_location`

**Sensors (8)**
- [ ] `sensor.melany_speed`
- [ ] `sensor.melany_shift_state`
- [ ] `sensor.melany_battery`
- [ ] `sensor.melany_range`
- [ ] `sensor.melany_charging_state`
- [ ] `sensor.melany_charger_voltage`
- [ ] `sensor.melany_charger_current`
- [ ] `sensor.melany_odometer`

**Binary Sensors (4)**
- [ ] `binary_sensor.melany_driving`
- [ ] `binary_sensor.melany_charging`
- [ ] `binary_sensor.melany_charge_port_open`
- [ ] `binary_sensor.melany_connected`

### 3.3 Entity Attributes
Check a sensor has proper attributes:
- [ ] `device_class` set correctly
- [ ] `unit_of_measurement` set correctly
- [ ] `state_class` set correctly (for statistics)

---

## Phase 4: Options Flow Testing

### 4.1 Access Options
1. Go to: **Settings → Devices & Services → Tesla Fleet Telemetry Local**
2. Click: **Configure**

- [ ] Options dialog opens
- [ ] Shows current values pre-filled

### 4.2 Modify Options
Test changing values:

| Test | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| Change topic | `new_topic` | Saves, integration reloads | [ ] |
| Change name | `MelanY 2` | Saves, device name updates | [ ] |
| Invalid broker | `bad:format:here` | Error shown | [ ] |
| Cancel | Click Cancel | No changes saved | [ ] |

---

## Phase 5: Diagnostics Testing

### 5.1 Download Diagnostics
1. Go to: **Settings → Devices & Services → Tesla Fleet Telemetry Local**
2. Click: **3 dots menu → Download diagnostics**

- [ ] JSON file downloads
- [ ] File contains configuration data
- [ ] VIN is redacted (privacy)
- [ ] No sensitive data exposed

### 5.2 Diagnostics Content
Check JSON contains:
```json
{
  "config_entry": {
    "data": {
      "kafka_broker": "***",
      "vehicle_vin": "LRWY***0528"  // Redacted
    }
  },
  "integration_data": {
    "connected": true/false,
    "last_update": "...",
    "entities_count": 13
  }
}
```

- [ ] Structure is correct
- [ ] Sensitive data redacted

---

## Phase 6: Error Handling

### 6.1 Kafka Disconnection
```bash
# Stop Kafka
docker stop kafka
```

- [ ] Integration shows "unavailable" state
- [ ] Entities show "unavailable"
- [ ] No crash in HA logs

### 6.2 Kafka Reconnection
```bash
# Start Kafka
docker start kafka
```

- [ ] Integration reconnects automatically
- [ ] Entities become available again
- [ ] No manual intervention needed

### 6.3 Integration Removal
1. Go to: **Settings → Devices & Services → Tesla Fleet Telemetry Local**
2. Click: **3 dots menu → Delete**

- [ ] Integration removed cleanly
- [ ] All entities removed
- [ ] No orphan entities remain
- [ ] No errors in logs

---

## Phase 7: Translation Testing

### 7.1 English (default)
- [ ] All UI text in English
- [ ] Error messages in English

### 7.2 Catalan
Change HA language to Catalan:
**Settings → System → General → Language → Català**

- [ ] Config Flow titles in Catalan
- [ ] Error messages in Catalan
- [ ] Options Flow in Catalan

---

## Phase 8: Log Analysis

### 8.1 Check for Errors
```bash
ssh root@192.168.6.41 "docker logs homeassistant 2>&1 | grep -i 'tesla_telemetry'"
```

- [ ] No ERROR level logs
- [ ] No WARNING about deprecated APIs
- [ ] No stack traces

### 8.2 Debug Logging
Add to configuration.yaml:
```yaml
logger:
  logs:
    custom_components.tesla_telemetry_local: debug
```

- [ ] Debug logs appear
- [ ] Shows Kafka connection attempts
- [ ] Shows message processing

---

## Results Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Installation | ✅ PASS | Files copied, deps installed |
| 2. Config Flow UI | ✅ PASS | Form works, validation OK |
| 3. Entity Verification | ✅ PASS | 13 entities created |
| 4. Options Flow | ✅ PASS | Can modify config |
| 5. Diagnostics | ✅ PASS | JSON with redacted data |
| 6. Error Handling | ⬜ SKIP | Not tested (no real Kafka) |
| 7. Translations | ✅ PASS | Catalan with accents fixed |
| 8. Log Analysis | ✅ PASS | No errors |

**Overall Result**: ✅ PASS

---

## Issues Found

| # | Description | Severity | Fix Status |
|---|-------------|----------|------------|
| 1 | Catalan accents missing in ca.json | Low | ✅ Fixed |
| 2 | Icon not showing (needs brands repo PR) | Low | ⏳ Pending |
| 3 | Entity IDs have `_2` suffix (old entities exist) | Info | N/A (clean install OK) |

---

## Notes

```
(Add any additional observations here)


```
