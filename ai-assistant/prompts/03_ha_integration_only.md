# Prompt: Home Assistant Integration Only

Use this if you already have the server running and just need help with the HA integration.

---

## Prompt

```
I already have Tesla Fleet Telemetry server running and publishing to MQTT. I need help setting up the Home Assistant integration.

Please read the CLAUDE_CONTEXT.md file in this project for context.

**My server details**:
- MQTT broker: [HA_IP:1883, e.g., 192.168.1.50:1883]
- MQTT topic base: [TOPIC, e.g., tesla]
- I've verified messages are arriving in MQTT: [YES/NO]

**My Home Assistant**:
- Installation type: [HA OS / Supervised / Core / Docker]
- Location of config: [e.g., /config or /home/user/.homeassistant]
- MQTT/Mosquitto add-on: [INSTALLED AND CONFIGURED? YES/NO]

**Vehicle details**:
- VIN: [17-CHARACTER VIN]
- Name: [FRIENDLY NAME]

Please help me:
1. Install the custom integration
2. Configure it via the UI
3. Verify entities are working
```

---

## Quick Verification Commands

Before asking for help, verify MQTT has data:

```bash
# Subscribe to Tesla topics (run from HA terminal or SSH)
mosquitto_sub -h localhost -t "tesla/#" -v

# Or with authentication
mosquitto_sub -h localhost -u mqtt_user -P your_password -t "tesla/#" -v
```

If you see JSON messages with your VIN, the server is working correctly.

Example output:
```
tesla/LRWYGCFS3RC210528/v/BatteryLevel {"value": 78}
tesla/LRWYGCFS3RC210528/v/VehicleSpeed {"value": 0}
tesla/LRWYGCFS3RC210528/v/Location {"latitude": 41.38, "longitude": 2.17}
```
