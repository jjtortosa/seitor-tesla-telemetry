# AI Setup Assistant

Get help setting up Tesla Fleet Telemetry using AI assistants like Claude, ChatGPT, or GitHub Copilot.

## How It Works

This folder contains context and prompts that help AI assistants understand the project and guide you through setup.

1. **CLAUDE_CONTEXT.md** - Complete project documentation for the AI
2. **prompts/** - Ready-to-use prompts for common scenarios

## Quick Start

### Option 1: Claude Code (Recommended)

If you have [Claude Code](https://claude.com/claude-code) installed:

```bash
# In the project directory
claude

# Then say:
> Help me set up Tesla Fleet Telemetry. Read ai-assistant/CLAUDE_CONTEXT.md first.
```

### Option 2: Web-based AI (Claude, ChatGPT, etc.)

1. Open your preferred AI assistant
2. Copy the contents of `CLAUDE_CONTEXT.md`
3. Paste it as context
4. Use one of the prompts from the `prompts/` folder

### Option 3: IDE with AI (Cursor, Copilot, etc.)

1. Open this project in your IDE
2. Open `CLAUDE_CONTEXT.md` in a tab
3. Ask the AI to help you with setup, referencing the context file

## Available Prompts

| Prompt | Use When |
|--------|----------|
| `01_initial_setup.md` | Starting from scratch |
| `02_troubleshooting.md` | Having issues with existing setup |
| `03_ha_integration_only.md` | Server works, need HA help |
| `04_server_only.md` | Only need server setup help |
| `05_nginx_proxy_manager.md` | Using NPM for SSL/proxy |

## Example Session

### Starting Setup

```
You: I want to set up Tesla Fleet Telemetry. I have:
     - Domain: tesla.mydomain.com
     - Ubuntu server at 192.168.1.100
     - Home Assistant at 192.168.1.50
     - Nginx Proxy Manager for SSL

     Please help me through the setup.

AI: I'll help you set up Tesla Fleet Telemetry. Let's start by
    verifying your prerequisites...
    [Guides through each step]
```

### Troubleshooting

```
You: My Fleet Telemetry container keeps restarting. Here are the logs:
     [paste logs]

AI: I can see the issue - your certificate is missing the intermediate
    chain. Let me show you how to fix this...
```

## Tips for Best Results

1. **Provide your environment details upfront**
   - Server IP, HA IP, domain name
   - What SSL method you're using
   - Your infrastructure (Docker, Proxmox, etc.)

2. **Share logs when troubleshooting**
   ```bash
   docker compose logs fleet-telemetry
   ```

3. **Verify each step before moving on**
   - The AI will give you verification commands
   - Run them and share the output

4. **Be specific about errors**
   - Exact error messages
   - When the error occurs
   - What you've already tried

## What the AI Can Help With

- Choosing the right setup for your infrastructure
- Step-by-step installation guidance
- Configuration file creation
- SSL certificate setup
- Network troubleshooting
- Home Assistant integration
- Debugging connection issues

## What You Still Need to Do Yourself

- Create Tesla Developer account
- Physically approve key pairing in vehicle
- Configure your router/firewall
- Pay for domain (if needed)

## Updating Context

If you modify the project structure, update `CLAUDE_CONTEXT.md` to reflect changes. This ensures AI assistants have accurate information.
