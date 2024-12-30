#!/bin/bash

source venv/bin/activate

export PYTHONPATH=$(pwd)

counter=0

while true; do
    sleep 300
    ((counter++))
    if [ $((counter % 4)) -eq 0 ]; then
      ./scripts/kill_fuzzer.sh
      ./scripts/start_fuzzer.sh
    else
      ./scripts/kill_runners.sh
      ./scripts/run_runners.sh
    fi
    grep -nr Seed logs/generator.log >> logs/compiler_crash.txt
    grep -nr Seed logs/generator.log >> logs/output_diff.txt
    python fuzz/results/print_contracts_with_output_difference.py >> logs/output_diff.txt
    python fuzz/results/print_contracts_with_compiler_error.py >> logs/compiler_crash.txt
    if ! pgrep -f "fuzz/generators/run_diff_ivy.py" > /dev/null; then
      python fuzz/generators/run_diff.py
    fi
done


done
