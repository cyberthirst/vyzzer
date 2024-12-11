#!/bin/bash

# Check if logs directory exists
if [ ! -d "logs" ]; then
    echo "Error: logs directory not found"
    exit 1
fi

# For each log file in the logs directory
for logfile in logs/*.log; do
    if [ -f "$logfile" ]; then
        echo "=== ${logfile##*/} ==="
        echo "Last 10 lines:"
        tail -n 10 "$logfile"
        echo -e "\n"
    fi
done

