# Tesla Developer Setup

This guide covers creating a Tesla Developer account, generating cryptographic keys, and registering your Fleet Telemetry application.

## Prerequisites

- ✅ Tesla account (same one used in your Tesla app)
- ✅ Domain configured (tesla-telemetry.seitor.com)
- ✅ SSL certificate generated
- ✅ `openssl` installed on your system

**Estimated time**: 2-3 hours (includes waiting for approval/sync)

---

## Step 1: Create Tesla Developer Account

### 1.1 Register at Tesla Developer Portal

1. Go to: **https://developer.tesla.com/**
2. Click **"Sign In"** (top right)
3. Log in with your **Tesla account** (same as mobile app)
4. Accept Tesla Developer Program Terms
5. Complete profile if prompted

### 1.2 Wait for Account Approval (if applicable)

Some accounts require manual approval. Check your email for confirmation.

**Typical wait time**: Instant to 24 hours

---

## Step 2: Generate Cryptographic Keys

Tesla Fleet API uses **ECDSA** (Elliptic Curve) keys for authentication. You'll need:

- **Private key**: Keep secret, used to sign requests
- **Public key**: Shared with Tesla, hosted on your domain

### 2.1 Generate EC Private Key

On your **local machine** or **Proxmox container**:

```bash
# Navigate to project directory
cd /opt/tesla-telemetry
# or on your local machine:
cd ~/Projects/seitor-tesla-telemetry/server

# Generate private key (secp256r1 curve, also known as prime256v1)
openssl ecparam -name prime256v1 -genkey -noout -out private_key.pem

# Verify key
openssl ec -in private_key.pem -text -noout
```

**Expected output**:
```
Private-Key: (256 bit)
priv:
    XX:XX:XX:...
pub:
    04:XX:XX:...
ASN1 OID: prime256v1
NIST CURVE: P-256
```

⚠️ **CRITICAL**: This private key is **extremely sensitive**. Protect it like a password!

### 2.2 Derive Public Key

```bash
# Extract public key from private key
openssl ec -in private_key.pem -pubout -out public_key.pem

# Verify public key
cat public_key.pem
```

**Expected output**:
```
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
-----END PUBLIC KEY-----
```

### 2.3 Create Tesla-Specific Public Key Format

Tesla requires the public key in a specific filename:

```bash
# Copy to Tesla-required filename
cp public_key.pem com.tesla.3p.public-key.pem

# Verify
cat com.tesla.3p.public-key.pem
```

**File size**: Should be ~178 bytes

---

## Step 3: Host Public Key on Your Domain

Tesla needs to fetch your public key from a specific URL:

**Required URL format**:
```
https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

### 3.1 Create Directory Structure

On your **Proxmox container**:

```bash
# Create .well-known directory
mkdir -p /var/www/tesla-telemetry/.well-known/appspecific

# Copy public key
cp /opt/tesla-telemetry/com.tesla.3p.public-key.pem \
   /var/www/tesla-telemetry/.well-known/appspecific/

# Set permissions
chmod 644 /var/www/tesla-telemetry/.well-known/appspecific/com.tesla.3p.public-key.pem
chown -R www-data:www-data /var/www/tesla-telemetry
```

### 3.2 Configure Nginx to Serve the File

Install Nginx:

```bash
apt install -y nginx
```

Create Nginx config:

```bash
nano /etc/nginx/sites-available/tesla-telemetry
```

**Content**:
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name tesla-telemetry.seitor.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tesla-telemetry.seitor.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/tesla-telemetry.seitor.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tesla-telemetry.seitor.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Root directory
    root /var/www/tesla-telemetry;

    # Serve .well-known directory
    location /.well-known/ {
        alias /var/www/tesla-telemetry/.well-known/;
        try_files $uri $uri/ =404;
    }

    # Health check endpoint (optional)
    location /health {
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # Default location
    location / {
        return 404;
    }
}
```

Enable site:

```bash
# Create symlink
ln -s /etc/nginx/sites-available/tesla-telemetry /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Reload Nginx
systemctl reload nginx
```

### 3.3 Verify Public Key is Accessible

From **any computer** (outside your network):

```bash
curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

**Expected output**:
```
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
-----END PUBLIC KEY-----
```

✅ If you see the public key, proceed!
❌ If error 404/502/connection refused, check Nginx logs:

```bash
tail -f /var/log/nginx/error.log
```

---

## Step 4: Create Tesla Application

### 4.1 Log in to Developer Portal

1. Go to: https://developer.tesla.com/
2. Click **"Dashboard"** → **"Create Application"**

### 4.2 Fill Application Details

**Application Information**:
- **Application Name**: `Home Assistant Telemetry` (or your choice)
- **Description**: `Self-hosted Fleet Telemetry for Home Assistant automation`
- **Website**: `https://ha.seitor.com` (optional)

**Scopes** (select these):
- ✅ `vehicle_device_data` (required for telemetry)
- ✅ `vehicle_location_data` (required for GPS)
- ✅ `vehicle_cmds` (required for commands, optional)
- ✅ `vehicle_charging_cmds` (optional, for future use)

**Redirect URIs**:
```
https://tesla-telemetry.seitor.com/oauth/callback
```

⚠️ **Important**: This URI must match exactly. We'll use it later for OAuth flow.

### 4.3 Register Domain for Public Key

In the application settings:

1. Scroll to **"Public Key"** section
2. Enter your domain: `tesla-telemetry.seitor.com`
3. Click **"Verify"**

Tesla will fetch:
```
https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```

✅ **Success**: Green checkmark if verification succeeds
❌ **Failure**: Error message if key not found

**Common errors**:
- URL not accessible (check Nginx)
- SSL certificate invalid (check Let's Encrypt)
- Wrong file path (check `.well-known/appspecific/`)

### 4.4 Save Application Credentials

After creating the application, Tesla will provide:

- **Client ID**: e.g., `ta-12345abcdefghijklmn`
- **Client Secret**: e.g., `ts-secret-...` (keep secret!)

⚠️ **COPY AND SAVE THESE!** You won't see the secret again.

Store in a secure location:

```bash
# On Proxmox container
nano /opt/tesla-telemetry/.env
```

**Content**:
```env
TESLA_CLIENT_ID=ta-12345abcdefghijklmn
TESLA_CLIENT_SECRET=ts-secret-your-secret-here
TESLA_DOMAIN=tesla-telemetry.seitor.com
```

**Permissions**:
```bash
chmod 600 /opt/tesla-telemetry/.env
chown root:root /opt/tesla-telemetry/.env
```

---

## Step 5: Virtual Key Pairing

Your vehicle needs to authorize the application to receive telemetry data.

### 5.1 Generate Pairing URL

**URL format**:
```
https://tesla.com/_ak/<YOUR_DOMAIN>
```

**Your URL**:
```
https://tesla.com/_ak/tesla-telemetry.seitor.com
```

### 5.2 Initiate Pairing

**Option A: Scan QR Code from Vehicle**

1. Generate QR code:

```bash
# On your computer
echo "https://tesla.com/_ak/tesla-telemetry.seitor.com" | qrencode -o tesla_pairing_qr.png
# Or use online QR generator: https://www.qr-code-generator.com/
```

2. Display QR code on your phone
3. In your **Tesla vehicle** (must be physically inside):
   - Navigate to: **Vehicle → Software → Additional Vehicle Information**
   - Tap **"Scan QR Code"**
   - Scan the QR code

**Option B: Manual Entry**

1. Open URL on your phone: `https://tesla.com/_ak/tesla-telemetry.seitor.com`
2. Log in with Tesla account
3. Select your vehicle: **MelanY**
4. Click **"Approve"**

### 5.3 Wait for Synchronization

After approval, Tesla needs to sync the virtual key to your vehicle.

**Expected wait time**:
- **Immediate**: If vehicle is connected to internet
- **Minutes to hours**: If vehicle is offline (will sync when it wakes up next time)

**Check sync status**:
1. Wake up your vehicle (open Tesla app)
2. Wait 5-10 minutes
3. Check vehicle's "Keys" section in app

---

## Step 6: Configure Telemetry Fields

Tell Tesla which data fields to send and how often.

### 6.1 Create Telemetry Configuration

Create a config file specifying the fields:

```bash
nano /opt/tesla-telemetry/telemetry_config.json
```

**Content**:
```json
{
  "hostname": "tesla-telemetry.seitor.com",
  "ca": "letsencrypt",
  "fields": {
    "Location": {
      "interval_seconds": 5
    },
    "Latitude": {
      "interval_seconds": 5
    },
    "Longitude": {
      "interval_seconds": 5
    },
    "ShiftState": {
      "interval_seconds": 1
    },
    "Speed": {
      "interval_seconds": 1
    },
    "Soc": {
      "interval_seconds": 60
    },
    "EstBatteryRange": {
      "interval_seconds": 60
    },
    "ChargingState": {
      "interval_seconds": 30
    },
    "ChargerVoltage": {
      "interval_seconds": 30
    },
    "ChargerActualCurrent": {
      "interval_seconds": 30
    },
    "ChargePortDoorOpen": {
      "interval_seconds": 30
    }
  }
}
```

**Field explanations**:
- `Location`/`Latitude`/`Longitude`: GPS coordinates (5s = real-time tracking)
- `ShiftState`: Gear position P/D/R/N (1s = instant driving detection)
- `Speed`: Current speed (1s = real-time)
- `Soc`: State of Charge / Battery % (60s = once per minute)
- `EstBatteryRange`: Remaining range (60s)
- `ChargingState`: Charging/Complete/Disconnected (30s)
- Charger fields: Voltage, current (30s)

⚠️ **Lower intervals = more data = more load**. Start conservative, adjust later.

### 6.2 Sign Configuration

Tesla requires the configuration to be signed with your private key:

```bash
cd /opt/tesla-telemetry

# Sign the config
openssl dgst -sha256 -sign private_key.pem \
  -out telemetry_config.sig \
  telemetry_config.json

# Convert signature to base64
base64 -w 0 telemetry_config.sig > telemetry_config.sig.b64
```

### 6.3 Send Configuration to Vehicle

**Method 1: Using Tesla Fleet API (vehicle-command)**

We'll set this up in the next guide. For now, note that you'll send the config via:

```bash
# Placeholder - will be detailed in server deployment
curl -X POST \
  https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles/<VEHICLE_ID>/command/set_telemetry_config \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d @telemetry_config_signed.json
```

**Method 2: Using `fleet-telemetry` server** (recommended)

The Fleet Telemetry server has a built-in endpoint for this. We'll configure it in the next guide.

---

## Step 7: Obtain OAuth Access Token

Tesla API requires OAuth 2.0 authentication. You need an access token.

### 7.1 Generate Authorization URL

**URL format**:
```
https://auth.tesla.com/oauth2/v3/authorize?
  client_id=<YOUR_CLIENT_ID>
  &redirect_uri=https://tesla-telemetry.seitor.com/oauth/callback
  &response_type=code
  &scope=vehicle_device_data vehicle_location_data vehicle_cmds
  &state=<RANDOM_STRING>
```

**Example** (replace `<YOUR_CLIENT_ID>`):
```
https://auth.tesla.com/oauth2/v3/authorize?client_id=ta-12345abcdefghijklmn&redirect_uri=https://tesla-telemetry.seitor.com/oauth/callback&response_type=code&scope=vehicle_device_data%20vehicle_location_data%20vehicle_cmds&state=abc123
```

### 7.2 Authorize Application

1. Open the URL in a browser
2. Log in with your Tesla account
3. Review permissions requested
4. Click **"Approve"**

Tesla will redirect to:
```
https://tesla-telemetry.seitor.com/oauth/callback?code=<AUTH_CODE>&state=abc123
```

⚠️ **Note**: This endpoint doesn't exist yet (will be created in server deployment). For now, copy the `code` parameter from the URL.

### 7.3 Exchange Code for Access Token

```bash
# Exchange authorization code for access token
curl -X POST https://auth.tesla.com/oauth2/v3/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=<YOUR_CLIENT_ID>" \
  -d "client_secret=<YOUR_CLIENT_SECRET>" \
  -d "code=<AUTH_CODE>" \
  -d "redirect_uri=https://tesla-telemetry.seitor.com/oauth/callback"
```

**Expected response**:
```json
{
  "access_token": "eyJ...very_long_token",
  "refresh_token": "eyJ...another_long_token",
  "expires_in": 28800,
  "token_type": "Bearer"
}
```

### 7.4 Save Tokens

```bash
# Save tokens securely
nano /opt/tesla-telemetry/tesla_tokens.json
```

**Content**:
```json
{
  "access_token": "eyJ...your_access_token",
  "refresh_token": "eyJ...your_refresh_token",
  "expires_at": 1699999999
}
```

**Permissions**:
```bash
chmod 600 /opt/tesla-telemetry/tesla_tokens.json
chown root:root /opt/tesla-telemetry/tesla_tokens.json
```

⚠️ **Access tokens expire after 8 hours**. You'll need to refresh them. We'll automate this in the server deployment.

---

## Step 8: Get Vehicle ID

You need your vehicle's ID to send commands.

```bash
# List vehicles
curl -X GET https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/vehicles \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

**Expected response**:
```json
{
  "response": [
    {
      "id": 1234567890123456789,
      "vehicle_id": 987654321,
      "vin": "5YJ3E1EA1MF000000",
      "display_name": "MelanY",
      "state": "asleep"
    }
  ]
}
```

Save the **`id`** field (not `vehicle_id`):

```bash
echo "TESLA_VEHICLE_ID=1234567890123456789" >> /opt/tesla-telemetry/.env
```

---

## Step 9: Validation Checklist

Before proceeding, verify:

- ✅ Tesla Developer account created
- ✅ Private key generated and secured
- ✅ Public key hosted and accessible at `https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem`
- ✅ Tesla application created and verified
- ✅ Client ID and secret saved
- ✅ Virtual key paired with vehicle
- ✅ Telemetry configuration created (telemetry_config.json)
- ✅ OAuth tokens obtained
- ✅ Vehicle ID retrieved

---

## Troubleshooting

### Public key verification fails

**Problem**: Tesla can't verify public key at `.well-known` URL

**Solutions**:
1. Test URL manually: `curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem`
2. Check Nginx logs: `tail -f /var/log/nginx/error.log`
3. Verify SSL certificate: `openssl s_client -connect tesla-telemetry.seitor.com:443`
4. Check file permissions: `ls -la /var/www/tesla-telemetry/.well-known/appspecific/`

### Virtual key pairing stuck

**Problem**: Pairing initiated but not syncing to vehicle

**Solutions**:
1. Wake up vehicle using Tesla app
2. Ensure vehicle has internet connectivity
3. Wait 15-30 minutes for sync
4. Try re-pairing from vehicle touchscreen directly

### OAuth authorization fails

**Problem**: Cannot obtain access token

**Solutions**:
1. Verify redirect URI matches exactly in application settings
2. Check client ID and secret are correct
3. Ensure authorization code hasn't expired (use within 10 minutes)
4. Check API endpoint region (use `.prd.na.` for North America, `.prd.eu.` for Europe)

### Vehicle ID not found

**Problem**: API returns empty vehicle list

**Solutions**:
1. Verify access token is valid (not expired)
2. Check scopes include `vehicle_device_data`
3. Ensure account owns the vehicle
4. Try refreshing token

---

## Next Steps

Tesla Developer setup complete! Proceed to:

**[04 - Server Deployment →](04_server_deployment.md)**

This will guide you through deploying the Fleet Telemetry server with Docker Compose and MQTT.
