# Prompt: Home Assistant Integration Only

Use this if you already have the server running and just need help with the HA integration.

---

## Prompt

```
I already have Tesla Fleet Telemetry server running and receiving data. I need help setting up the Home Assistant integration.

Please read the CLAUDE_CONTEXT.md file in this project for context.

**My server details**:
- Kafka broker: [IP:PORT, e.g., 192.168.1.100:9092]
- Kafka topic: [TOPIC, e.g., tesla_telemetry]
- I've verified messages are arriving in Kafka: [YES/NO]

**My Home Assistant**:
- Installation type: [HA OS / Supervised / Core / Docker]
- Location of config: [e.g., /config or /home/user/.homeassistant]

**Vehicle details**:
- VIN: [17-CHARACTER VIN]
- Name: [FRIENDLY NAME]

Please help me:
1. Install the custom integration
2. Configure it correctly
3. Verify entities are working
```

---

## Quick Verification Commands

Before asking for help, verify Kafka has data:

```bash
# Check topic exists
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# See recent messages (wait a few seconds)
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic tesla_telemetry \
  --from-beginning \
  --max-messages 5
```

If you see JSON messages with your VIN, the server is working correctly.
