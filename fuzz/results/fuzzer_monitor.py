from dataclasses import dataclass
from typing import Optional
import subprocess
import time
from bson import ObjectId
from fuzz.helpers.db import get_mongo_client
import os
import glob


@dataclass
class FuzzerStats:
    generated: int = 0
    compiler_errors: int = 0
    nagini_runs: int = 0
    adder_runs: int = 0
    verified: int = 0

    def diff(self, other: 'FuzzerStats') -> 'FuzzerStats':
        return FuzzerStats(
            self.generated - other.generated,
            self.compiler_errors - other.compiler_errors,
            self.nagini_runs - other.nagini_runs,
            self.adder_runs - other.adder_runs,
            self.verified - other.verified
        )


class FuzzerMonitor:
    INTERVAL = 60
    RESTART_THRESHOLD = 2
    RAM_CLEANUP_INTERVAL = 300

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host
        self.port = port
        self.total_time = 0
        self._init_file_counters()
        self.reset_state()

    def _init_file_counters(self):
        """Initialize file counters based on existing files"""
        # Get the next available benchmark number
        bench_files = glob.glob('results/bench/data*.txt')
        self.bench_counter = len(bench_files) + 1

        # Get the next available crash number
        crash_files = glob.glob('results/crashes/crash*.txt')
        self.crash_counter = len(crash_files) + 1

        # Get the next available storage diff number
        diff_files = glob.glob('results/storage-diff/diff*.txt')
        self.diff_counter = len(diff_files) + 1

    def reset_state(self):
        """Reset all internal state to default values"""
        self.db = get_mongo_client(self.host, self.port)
        self.compilation_log = self.db['compilation_log']
        self.run_results = self.db['run_results']
        self.verification_results = self.db['verification_results']
        self.elapsed_time = 0
        self.error_counts = {"generator": 0, "runner": 0}
        self.stats = FuzzerStats()
        self.seed = self._extract_seed()
        self.first_pass = True

        # Create new benchmark and metadata files (empty)
        self.bench_file = f'results/bench/data{self.bench_counter}.txt'
        self.metadata_file = f'results/bench/bench-metadata{self.bench_counter}.txt'
        # Just create empty files
        open(self.bench_file, 'w').close()
        open(self.metadata_file, 'w').close()

    def _extract_seed(self) -> int:
        with open('logs/generator.log', 'r') as file:
            while True:
                if len(file.readlines()) >= 50:
                    file.seek(0)
                    for line in (next(file) for _ in range(50)):
                        if "Seed" in line:
                            return int(line.split("Seed: ")[1])
                file.seek(0)
                with open(self.metadata_file, 'a') as mf:
                    mf.write("waiting for seed\n")
                time.sleep(5)

    def _get_stats(self) -> FuzzerStats:
        return FuzzerStats(
            generated=self.compilation_log.count_documents({}),
            compiler_errors=self.compilation_log.count_documents({"error_type": {"$ne": None}}),
            nagini_runs=self.run_results.count_documents({"result_nagini": {"$exists": True}}),
            adder_runs=self.run_results.count_documents({"result_adder": {"$exists": True}}),
            verified=self.run_results.count_documents({"is_handled": True})
        )

    def _log_metrics(self, current: FuzzerStats, diff: FuzzerStats):
        metrics = {
            # Differences
            "diff_generated_contracts": diff.generated,
            "diff_compilation_errors": diff.compiler_errors,
            "diff_nagini_runs": diff.nagini_runs,
            "diff_adder_runs": diff.adder_runs,
            "diff_verified_results": diff.verified,
            # Totals
            "total_generated_contracts": current.generated,
            "total_compilation_errors": current.compiler_errors,
            "total_nagini_runs": current.nagini_runs,
            "total_adder_runs": current.adder_runs,
            "total_verified_results": current.verified,
            # Time and State
            "elapsed_time": self.elapsed_time,
            "current_seed": self.seed,
            "generator_errors": self.error_counts["generator"],
            "runner_errors": self.error_counts["runner"]
        }

        with open(self.bench_file, 'a') as f:
            for key, value in metrics.items():
                f.write(f"{key}:{value}\n")
            f.write("\n")  # Empty line for readability

    def _log_compiler_crashes(self):
        crashes = self.compilation_log.find({
            "error_type": {"$ne": None},
            "error_message": {"$regex": "This is an unhandled"}
        })

        for crash in crashes:
            crash_file = f'results/crashes/crash{self.crash_counter}.txt'
            with open(crash_file, 'w') as f:
                f.write(f"seed:{self.seed}\n"
                        f"time:{self.elapsed_time}\n"
                        f"error_message:\n{crash['error_message']}\n"
                        "==========================================\n")
            self.crash_counter += 1

    def _log_verification_discrepancies(self):
        discrepancies = self.verification_results.find({
            "results": {
                "$elemMatch": {
                    "$or": [
                        {"results.Storage": {"$ne": None}},
                        {"results.Return_Value": {"$ne": None}}
                    ]
                }
            },
            "logged_to_file": {"$ne": True}
        })

        for disc in discrepancies:
            contract = self.compilation_log.find_one({"_id": ObjectId(disc['generation_id'])})
            diff_file = f'results/storage-diff/diff{self.diff_counter}.txt'
            with open(diff_file, 'w') as f:
                f.write(f"seed:{self.seed}\n"
                        f"total_time:{self.total_time}\n"
                        f"time_elapsed:{self.elapsed_time}\n"
                        f"id:{disc['generation_id']}\n"
                        f"verification_discrepancy:\n{disc['results']}\n"
                        f"original_contract:\n{contract['generation_result_nagini']}\n"
                        "===================================\n")
            self.diff_counter += 1

            # Mark as logged
            self.verification_results.update_one(
                {"_id": disc["_id"]},
                {"$set": {"logged_to_file": True}}
            )

    def _handle_service_health(self, diff: FuzzerStats):
        if self.first_pass:
            self.first_pass = False
            return

        # Check for stalled runners
        if diff.nagini_runs == 0 or diff.adder_runs == 0 or self.elapsed_time % self.RAM_CLEANUP_INTERVAL == 0:
            with open(self.metadata_file, 'a') as f:
                f.write("monitor_event:restarting_runners\n")
            subprocess.run(['./scripts/kill_runners.sh'], shell=True,
                           stdout=open(self.metadata_file, 'a'),
                           stderr=subprocess.STDOUT)
            subprocess.run(['./scripts/run_runners.sh'], shell=True,
                           stdout=open(self.metadata_file, 'a'),
                           stderr=subprocess.STDOUT)
            self.error_counts["runner"] += 1
        else:
            self.error_counts["runner"] = 0

        # Check for stalled generator
        if diff.generated == 0:
            with open(self.metadata_file, 'a') as f:
                f.write("monitor_event:restarting_generator\n")
            subprocess.run(['./scripts/run_generator.sh'], shell=True,
                           stdout=open(self.metadata_file, 'a'),
                           stderr=subprocess.STDOUT)
            self.error_counts["generator"] += 1
        else:
            self.error_counts["generator"] = 0

        # Full restart if error threshold reached
        if any(count >= self.RESTART_THRESHOLD for count in self.error_counts.values()):
            with open(self.metadata_file, 'a') as f:
                f.write("monitor_event:full_restart_triggered\n")
            subprocess.run(['./scripts/kill_fuzzer.sh'], shell=True,
                           stdout=open(self.metadata_file, 'a'),
                           stderr=subprocess.STDOUT)
            subprocess.run(['./scripts/start_fuzzer.sh'], shell=True,
                           stdout=open(self.metadata_file, 'a'),
                           stderr=subprocess.STDOUT)
            self.bench_counter += 1  # Increment before reset
            self.reset_state()

    def monitor_cycle(self):
        try:
            current_stats = self._get_stats()
            diff_stats = current_stats.diff(self.stats)

            self._log_metrics(current_stats, diff_stats)
            self._log_compiler_crashes()
            self._log_verification_discrepancies()
            self._handle_service_health(diff_stats)

            self.stats = current_stats
            self.elapsed_time += self.INTERVAL
            self.total_time += self.INTERVAL
        except Exception as e:
            with open(self.metadata_file, 'a') as f:
                f.write(f"monitor_event:error\nerror_message:{str(e)}\n")
            self.bench_counter += 1  # Increment before reset
            self.reset_state()


def main():
    monitor = FuzzerMonitor()
    while True:
        monitor.monitor_cycle()
        time.sleep(monitor.INTERVAL)


if __name__ == "__main__":
    main()
