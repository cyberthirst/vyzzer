#!/bin/bash

export PYTHONPATH=$(pwd)

source venv/bin/activate

echo "Starting generator.."
python fuzz/generators/run_diff_ivy.py > logs/generator.log 2>&1 &

deactivate
