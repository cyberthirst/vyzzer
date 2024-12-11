#!/bin/bash

mkdir -p logs

# Stop and remove any existing containers with same ports
docker stop $(docker ps -q --filter publish=27017)
docker stop $(docker ps -q --filter publish=5672)
docker stop $(docker ps -q --filter publish=5673)

# Start Docker containers
echo "Starting MongoDB..."
docker run -d -p 27017:27017 mongo

echo "Starting RabbitMQ instance 1..."
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management

echo "Starting RabbitMQ instance 2..."
docker run -d -p 5673:5672 -p 15673:15672 rabbitmq:management

echo "Waiting 10s for services to start up..."
sleep 10

export PYTHONPATH=$(pwd)

# Start first processes in default venv
source venv/bin/activate
echo "Starting adder service fuzzing..."
python fuzz/runners/runner_ivy.py > logs/adder_fuzzing.log 2>&1 &

echo "Starting nagini service fuzzing..."
SERVICE_NAME=nagini python fuzz_runners/runner_nagini.py > logs/nagini_fuzzing.log 2>&1 &

echo "Starting diff ivy generator..."
python fuzz/generators/run_diff_ivy.py > logs/diff_ivy.log 2>&1 &

echo "Starting ivy verifier..."
python fuzz/verifiers/verifier_ivy.py > logs/verifier_ivy.log 2>&1 &
deactivate

echo "All processes started. Logs are being written to the logs/ directory."
echo "You can monitor the logs with: tail -f logs/*.log"
echo "To stop the processes later, exit the shell.

