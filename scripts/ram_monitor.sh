#!/bin/bash

source venv/bin/activate

while true; do
    sleep 300
    ./scripts/kill_runners.sh
    ./scripts/run_runners.sh
done
