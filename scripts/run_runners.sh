#!/bin/bash

export PYTHONPATH=$(pwd)

source venv/bin/activate

echo "Starting adder runner..."
SERVICE_NAME=adder python fuzz/runners/runner_ivy.py > logs/adder_runner.log 2>&1 &

echo "Starting nagini runner..."
SERVICE_NAME=nagini python fuzz/runners/runner_nagini.py > logs/nagini_runner.log 2>&1 &

./scripts/ram_monitor.sh &

deactivate

