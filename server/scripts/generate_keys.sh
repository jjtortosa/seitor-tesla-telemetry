#!/bin/bash
#
# Generate ECDSA keys for Tesla Fleet API
# Usage: ./generate_keys.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
KEYS_DIR="$SERVER_DIR/keys"

echo "🔐 Tesla Fleet API Key Generation"
echo "=================================="
echo

# Create keys directory
mkdir -p "$KEYS_DIR"
cd "$KEYS_DIR"

# Check if keys already exist
if [ -f "private_key.pem" ]; then
    echo "⚠️  Private key already exists!"
    read -p "Do you want to overwrite it? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi
    echo
fi

# Generate private key
echo "📝 Generating EC private key (secp256r1 curve)..."
openssl ecparam -name prime256v1 -genkey -noout -out private_key.pem

if [ $? -ne 0 ]; then
    echo "❌ Error generating private key"
    exit 1
fi

echo "✅ Private key generated: $KEYS_DIR/private_key.pem"
echo

# Derive public key
echo "📝 Deriving public key..."
openssl ec -in private_key.pem -pubout -out public_key.pem

if [ $? -ne 0 ]; then
    echo "❌ Error deriving public key"
    exit 1
fi

echo "✅ Public key generated: $KEYS_DIR/public_key.pem"
echo

# Create Tesla-specific public key filename
echo "📝 Creating Tesla-specific public key format..."
cp public_key.pem com.tesla.3p.public-key.pem

echo "✅ Tesla public key: $KEYS_DIR/com.tesla.3p.public-key.pem"
echo

# Set secure permissions
chmod 600 private_key.pem
chmod 644 public_key.pem com.tesla.3p.public-key.pem

# Verify keys
echo "🔍 Verifying keys..."
echo

echo "Private key details:"
openssl ec -in private_key.pem -text -noout | head -n 10
echo

echo "Public key details:"
openssl ec -in public_key.pem -pubin -text -noout | head -n 10
echo

# Display next steps
echo "✅ Key generation complete!"
echo
echo "📋 Next steps:"
echo "1. Host the public key at:"
echo "   https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem"
echo
echo "2. Verify it's accessible:"
echo "   curl https://tesla-telemetry.seitor.com/.well-known/appspecific/com.tesla.3p.public-key.pem"
echo
echo "3. Register your domain in Tesla Developer Portal"
echo "   https://developer.tesla.com/"
echo
echo "⚠️  IMPORTANT: Keep private_key.pem SECRET!"
echo "   Never commit it to git or share it."
echo

# Add to .gitignore
GITIGNORE_FILE="$SERVER_DIR/.gitignore"
if [ -f "$GITIGNORE_FILE" ]; then
    if ! grep -q "private_key.pem" "$GITIGNORE_FILE"; then
        echo "private_key.pem" >> "$GITIGNORE_FILE"
        echo "✅ Added private_key.pem to .gitignore"
    fi
else
    echo "private_key.pem" > "$GITIGNORE_FILE"
    echo "*.pem" >> "$GITIGNORE_FILE"
    echo "*.key" >> "$GITIGNORE_FILE"
    echo "✅ Created .gitignore"
fi

echo
echo "Done! 🎉"
