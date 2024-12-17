#!/bin/bash

pkill -f "python fuzz/runners/runner_nagini.py"
pkill -f "python fuzz/runners/runner_ivy.py"
pkill -f "./scripts/ram_monitor.sh"

echo "Runners were killed"
