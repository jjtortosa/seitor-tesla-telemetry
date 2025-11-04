#!/bin/bash
#
# Validate SSL certificate for Tesla Fleet Telemetry
# Based on Tesla's check_server_cert.sh
# Usage: ./validate_cert.sh tesla-telemetry.seitor.com
#

set -e

DOMAIN="${1:-tesla-telemetry.seitor.com}"
PORT="${2:-443}"

echo "🔐 SSL Certificate Validation for Tesla Fleet Telemetry"
echo "========================================================="
echo
echo "Domain: $DOMAIN"
echo "Port: $PORT"
echo

# Check if domain resolves
echo "📡 Checking DNS resolution..."
if ! host "$DOMAIN" > /dev/null 2>&1; then
    echo "❌ Domain $DOMAIN does not resolve"
    echo "   Fix DNS configuration first"
    exit 1
fi

DNS_IP=$(host "$DOMAIN" | awk '/has address/ { print $4 }' | head -n 1)
echo "✅ Domain resolves to: $DNS_IP"
echo

# Check if port is open
echo "🔌 Checking port $PORT connectivity..."
if ! timeout 5 bash -c "</dev/tcp/$DOMAIN/$PORT" 2>/dev/null; then
    echo "❌ Cannot connect to $DOMAIN:$PORT"
    echo "   Check port forwarding and firewall"
    exit 1
fi

echo "✅ Port $PORT is accessible"
echo

# Fetch and validate certificate
echo "🔍 Fetching SSL certificate..."
CERT_INFO=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName 2>/dev/null)

if [ -z "$CERT_INFO" ]; then
    echo "❌ Failed to fetch certificate"
    exit 1
fi

echo "✅ Certificate retrieved"
echo

# Display certificate details
echo "📋 Certificate Details:"
echo "----------------------"
echo "$CERT_INFO"
echo

# Check certificate validity
CERT_EXPIRY=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$CERT_EXPIRY" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$CERT_EXPIRY" +%s 2>/dev/null)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

echo "⏱️  Certificate Expiry:"
echo "   Expires: $CERT_EXPIRY"
echo "   Days until expiry: $DAYS_UNTIL_EXPIRY"

if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
    echo "   ❌ Certificate EXPIRED!"
    exit 1
elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    echo "   ⚠️  Certificate expires soon (< 30 days)"
else
    echo "   ✅ Certificate valid"
fi
echo

# Check if certificate matches domain
echo "🔍 Validating certificate domain..."
CERT_CN=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -subject | sed -n 's/.*CN = \(.*\)/\1/p')

if [[ "$CERT_CN" == *"$DOMAIN"* ]]; then
    echo "✅ Certificate CN matches domain: $CERT_CN"
else
    # Check SAN (Subject Alternative Name)
    CERT_SAN=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -ext subjectAltName | grep "DNS:$DOMAIN")

    if [ -n "$CERT_SAN" ]; then
        echo "✅ Certificate SAN includes domain"
    else
        echo "⚠️  Certificate CN does not match domain"
        echo "   CN: $CERT_CN"
        echo "   Expected: $DOMAIN"
    fi
fi
echo

# Check certificate issuer
CERT_ISSUER=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -issuer | sed 's/issuer=//')

echo "📜 Certificate Issuer:"
echo "   $CERT_ISSUER"

if [[ "$CERT_ISSUER" == *"Let's Encrypt"* ]] || [[ "$CERT_ISSUER" == *"DigiCert"* ]] || [[ "$CERT_ISSUER" == *"Sectigo"* ]]; then
    echo "   ✅ Trusted CA"
else
    echo "   ⚠️  Unknown CA (may not be trusted by Tesla)"
fi
echo

# Test TLS handshake
echo "🤝 Testing TLS handshake..."
TLS_TEST=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" 2>&1 | grep "Verification")

if [[ "$TLS_TEST" == *"OK"* ]]; then
    echo "✅ TLS handshake successful"
else
    echo "⚠️  TLS handshake verification:"
    echo "   $TLS_TEST"
fi
echo

# Check supported TLS versions
echo "🔐 Checking TLS versions..."
for VERSION in tls1_2 tls1_3; do
    if echo | openssl s_client -connect "$DOMAIN:$PORT" -servername "$DOMAIN" -"$VERSION" > /dev/null 2>&1; then
        echo "   ✅ $(echo $VERSION | tr '_' '.' | tr '[:lower:]' '[:upper:]') supported"
    else
        echo "   ❌ $(echo $VERSION | tr '_' '.' | tr '[:lower:]' '[:upper:]') not supported"
    fi
done
echo

# Final summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ERRORS=0
WARNINGS=0

if [ $DAYS_UNTIL_EXPIRY -lt 0 ]; then
    echo "❌ Certificate expired"
    ERRORS=$((ERRORS + 1))
elif [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
    echo "⚠️  Certificate expires soon"
    WARNINGS=$((WARNINGS + 1))
fi

if [[ "$TLS_TEST" != *"OK"* ]]; then
    echo "⚠️  TLS verification issues detected"
    WARNINGS=$((WARNINGS + 1))
fi

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo
    echo "✅ All checks passed!"
    echo "   Certificate is valid for Tesla Fleet Telemetry"
    echo
    exit 0
elif [ $ERRORS -gt 0 ]; then
    echo
    echo "❌ Certificate validation failed ($ERRORS error(s))"
    echo "   Fix issues before proceeding"
    echo
    exit 1
else
    echo
    echo "⚠️  Certificate has warnings ($WARNINGS warning(s))"
    echo "   Consider fixing before production use"
    echo
    exit 0
fi
