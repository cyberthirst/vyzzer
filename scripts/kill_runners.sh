#!/bin/bash

pkill -f "python fuzz/runners/runner_nagini.py"
pkill -f "python fuzz/runners/runner_ivy.py"

echo "Runners were killed"
