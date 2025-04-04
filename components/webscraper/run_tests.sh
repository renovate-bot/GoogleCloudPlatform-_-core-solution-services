#!/bin/bash
set -e  # Exit on any error

# Check if firebase-tools is installed
if ! command -v firebase &> /dev/null; then
    echo "Firebase CLI not found. Installing firebase-tools..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    bash "$PROJECT_ROOT/utils/install_firebase.sh"
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed"
    exit 1
fi

# Setup Python virtual environment and install storage emulator
if [ ! -d ".venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install gcp-storage-emulator
fi

# Start storage emulator if not already running
echo "Checking Storage emulator status..."
if curl -s http://localhost:9023 > /dev/null; then
    echo "Storage emulator already running"
else
    echo "Starting Storage emulator..."
    .venv/bin/gcp-storage-emulator start &

    # Wait for emulator to be ready
    echo "Waiting for Storage emulator to start..."
    timeout=30
    while ! curl -s http://localhost:9023 > /dev/null; do
        if [ $timeout -le 0 ]; then
            echo "Timeout waiting for Storage emulator to start"
            exit 1
        fi
        timeout=$((timeout - 1))
        sleep 1
    done
    echo "Storage emulator is ready!"
fi

# Check if firestore emulator is already running
echo "Checking Firestore emulator status..."
if curl -s http://localhost:8080 > /dev/null; then
    echo "Firestore emulator already running"
else
    echo "Starting Firestore emulator..."
    firebase emulators:start --only firestore --project fake-project &

    # Wait for emulator to be ready
    echo "Waiting for emulator to start..."
    timeout=30
    while ! curl -s http://localhost:8080 > /dev/null; do
        if [ $timeout -le 0 ]; then
            echo "Timeout waiting for emulator to start"
            exit 1
        fi
        timeout=$((timeout - 1))
        sleep 1
    done
    echo "Firestore emulator is ready!"
fi

# Run the tests
echo "Running tests..."
STORAGE_EMULATOR_HOST=http://localhost:9023 go test -v ./...