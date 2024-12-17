#!/bin/bash

# Find and kill the diff ivy generator process
pkill -f "python fuzz/generators/run_diff_ivy.py"

echo "Diff ivy generator has been stopped"
