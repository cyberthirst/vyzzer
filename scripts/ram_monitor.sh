#!/bin/bash

source venv/bin/activate

while true; do
    # Get available RAM in MB
    available_ram=$(free -m | awk '/^Mem:/ {print $7}')

    echo "Available RAM: $available_ram MB"

    # Check if available RAM is less than 500MB
    if [ $available_ram -lt 500 ]; then
        echo "Low memory detected! Restarting runners..."
        ./scripts/kill_runners.sh
        sleep 0.5
        ./scripts/run_runners.sh
    fi

    # Wait 20 seconds before next check
    sleep 20
done
