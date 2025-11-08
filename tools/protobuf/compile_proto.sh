#!/bin/bash
#
# Tesla Fleet Telemetry Protobuf Compilation Script
#
# This script compiles Tesla's vehicle_data.proto schema into Python bindings
# for use in the Home Assistant custom integration.
#
# Usage:
#   ./compile_proto.sh
#
# Requirements:
#   - Python 3.9+
#   - protobuf package (pip install protobuf)
#   - protoc compiler (included with protobuf package)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROTO_FILE="${SCRIPT_DIR}/vehicle_data.proto"
OUTPUT_DIR="${SCRIPT_DIR}"
HA_INTEGRATION_DIR="${PROJECT_ROOT}/ha-integration/custom_components/tesla_telemetry_local"

echo -e "${GREEN}Tesla Fleet Telemetry Protobuf Compiler${NC}"
echo "=========================================="
echo ""

# Check if proto file exists
if [ ! -f "${PROTO_FILE}" ]; then
    echo -e "${RED}Error: vehicle_data.proto not found at ${PROTO_FILE}${NC}"
    echo "Please download it first:"
    echo "  curl -L -o ${PROTO_FILE} https://raw.githubusercontent.com/teslamotors/fleet-telemetry/main/protos/vehicle_data.proto"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found vehicle_data.proto ($(wc -l < "${PROTO_FILE}") lines)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python 3 available: $(python3 --version)"

# Check if protoc is available
if ! command -v protoc &> /dev/null; then
    echo -e "${RED}Error: protoc compiler not found${NC}"
    echo "Please install protobuf compiler:"
    echo "  macOS: brew install protobuf"
    echo "  Ubuntu/Debian: sudo apt-get install protobuf-compiler"
    echo "  Or: pip3 install grpcio-tools"
    exit 1
fi

echo -e "${GREEN}✓${NC} Protoc compiler available: $(protoc --version)"
echo ""

# Compile the proto file
echo "Compiling vehicle_data.proto..."
protoc --python_out="${OUTPUT_DIR}" \
       --proto_path="${SCRIPT_DIR}" \
       "${PROTO_FILE}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Compilation successful!"
    echo ""

    # Check if output file was generated
    GENERATED_FILE="${OUTPUT_DIR}/vehicle_data_pb2.py"
    if [ -f "${GENERATED_FILE}" ]; then
        echo -e "${GREEN}✓${NC} Generated: ${GENERATED_FILE}"
        echo "  Size: $(wc -c < "${GENERATED_FILE}") bytes"
        echo "  Lines: $(wc -l < "${GENERATED_FILE}") lines"
        echo ""

        # Copy to Home Assistant integration
        echo "Copying to Home Assistant integration..."
        cp "${GENERATED_FILE}" "${HA_INTEGRATION_DIR}/"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓${NC} Copied to: ${HA_INTEGRATION_DIR}/vehicle_data_pb2.py"
            echo ""
            echo -e "${GREEN}SUCCESS!${NC} Protobuf compilation complete."
            echo ""
            echo "Next steps:"
            echo "  1. Verify the generated file: ${HA_INTEGRATION_DIR}/vehicle_data_pb2.py"
            echo "  2. Test imports: python3 -c 'from custom_components.tesla_telemetry_local import vehicle_data_pb2'"
            echo "  3. Update kafka_consumer.py to use Protobuf parsing"
            echo "  4. Restart Home Assistant to load the new integration"
        else
            echo -e "${RED}Error: Failed to copy to Home Assistant integration${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: Expected output file not found: ${GENERATED_FILE}${NC}"
        exit 1
    fi
else
    echo -e "${RED}Error: Compilation failed${NC}"
    exit 1
fi
