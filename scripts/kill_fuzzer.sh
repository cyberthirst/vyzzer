#!/bin/bash

# Kill all Python processes containing 'fuzz'
echo "Stopping Python processes..."
pkill -f "python.*runners"
pkill -f "python.*generators"
pkill -f "python.*verifiers"
#pkill -f "./scripts/ram_monitor.sh"

# Define ports used by containers
PORTS=(27017 5672 5673 15672 15673)

# Stop and remove containers using these ports
echo "Stopping Docker containers..."
for PORT in "${PORTS[@]}"; do
    CONTAINERS=$(docker ps -q --filter publish=$PORT)
    if [ ! -z "$CONTAINERS" ]; then
        echo "Stopping containers using port $PORT..."
        docker stop $CONTAINERS
        docker rm $CONTAINERS
    fi
done

echo "Cleanup complete!"

