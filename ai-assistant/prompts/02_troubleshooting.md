# Prompt: Troubleshooting

Copy and paste this when you have issues with your setup.

---

## Prompt Template

```
I've set up Tesla Fleet Telemetry but I'm having issues.

Please read the CLAUDE_CONTEXT.md file in this project for context.

**Problem**: [DESCRIBE YOUR ISSUE]

**What I see**:
- [SYMPTOMS, ERROR MESSAGES, ETC.]

**What I've tried**:
- [STEPS YOU'VE ALREADY TAKEN]

**My setup**:
- Domain: [YOUR DOMAIN]
- Server IP: [YOUR SERVER IP]
- Home Assistant IP: [YOUR HA IP]
- SSL: [HOW YOU GOT YOUR CERTIFICATES]
- MQTT: [MOSQUITTO ADD-ON INSTALLED? YES/NO]

**Relevant logs**:
```
[PASTE LOGS HERE]
```

Please help me diagnose and fix this issue.
```

---

## Common Issues to Mention

### No messages arriving
```
Problem: MQTT topics are empty, no telemetry data arriving.

What I see:
- Fleet Telemetry container is running
- No errors in fleet-telemetry logs
- mosquitto_sub shows nothing on tesla/# topics

What I've tried:
- Verified DNS resolves correctly
- Checked port 443 is open
- Verified MQTT broker credentials
```

### HA entities unavailable
```
Problem: All Tesla entities show "Unavailable" in Home Assistant.

What I see:
- Integration loaded without errors
- Entities were created
- All entities show "Unavailable"

What I've tried:
- Restarted Home Assistant
- Verified MQTT messages with mosquitto_sub
- Checked topic base matches server config
```

### Certificate errors
```
Problem: Fleet Telemetry container keeps restarting with TLS errors.

What I see:
- Container restart loop
- Error in logs about certificates

Relevant logs:
[PASTE docker compose logs fleet-telemetry OUTPUT]
```

### MQTT connection failed
```
Problem: Fleet Telemetry cannot connect to MQTT broker.

What I see:
- Fleet Telemetry logs show MQTT connection errors
- Mosquitto broker is running

What I've tried:
- Verified MQTT credentials
- Tested connection with mosquitto_pub
- Checked network connectivity from server to HA
```
