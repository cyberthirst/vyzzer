from dataclasses import dataclass
from typing import Optional
import subprocess
import time
from bson import ObjectId
from fuzz.helpers.db import get_mongo_client


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
        self.reset_state()

    def reset_state(self):
        """Reset all internal state to default values"""
        self.db = get_mongo_client(self.host, self.port)
        self.compilation_log = self.db['compilation_log']
        self.run_results = self.db['run_results']
        self.verification_results = self.db['verification_results']
        self.elapsed_time = 0
        self.error_counts = {"generator": 0, "runner": 0}
        self.stats = FuzzerStats()  # Start with zeros
        self.seed = self._extract_seed()
        print("monitor_event:state_reset")

    def _extract_seed(self) -> int:
        with open('logs/generator.log', 'r') as file:
            while True:
                if len(file.readlines()) >= 50:
                    file.seek(0)
                    for line in (next(file) for _ in range(50)):
                        if "Seed" in line:
                            return int(line.split("Seed: ")[1])
                file.seek(0)
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

        for key, value in metrics.items():
            print(f"{key}:{value}")

    def _log_compiler_crashes(self):
        with open('logs/compiler_crash.txt', 'a') as f:
            crashes = self.compilation_log.find({
                "error_type": {"$ne": None},
                "error_message": {"$regex": "This is an unhandled"}
            })

            for crash in crashes:
                f.write(f"seed:{self.seed}\n"
                        f"error_message:\n{crash['error_message']}\n"
                        "==========================================\n")

    def _log_verification_discrepancies(self):
        with open('logs/output_diff.txt', 'a') as f:
            discrepancies = self.verification_results.find({
                "results": {
                    "$elemMatch": {
                        "$or": [
                            {"results.Storage": {"$ne": None}},
                            {"results.Return_Value": {"$ne": None}}
                        ]
                    }
                }
            })

            for disc in discrepancies:
                contract = self.compilation_log.find_one({"_id": ObjectId(disc['generation_id'])})
                f.write(f"seed:{self.seed}\n"
                        f"verification_discrepancy:\n{disc['results']}\n"
                        f"original_contract:\n{contract['generation_result_nagini']}\n"
                        "===================================\n")

    def _handle_service_health(self, diff: FuzzerStats):
        # Check for stalled runners
        if diff.nagini_runs == 0 or diff.adder_runs == 0 or self.elapsed_time % self.RAM_CLEANUP_INTERVAL == 0:
            print("monitor_event:restarting_runners")
            subprocess.run(['./scripts/kill_runners.sh'], shell=True)
            subprocess.run(['./scripts/run_runners.sh'], shell=True)
            self.error_counts["runner"] += 1
        else:
            self.error_counts["runner"] = 0

        # Check for stalled generator
        if diff.generated == 0:
            print("monitor_event:restarting_generator")
            subprocess.run(['./scripts/run_generator.sh'], shell=True)
            self.error_counts["generator"] += 1
        else:
            self.error_counts["generator"] = 0

        # Full restart if error threshold reached
        if any(count >= self.RESTART_THRESHOLD for count in self.error_counts.values()):
            print("monitor_event:full_restart_triggered")
            subprocess.run(['./scripts/kill_fuzzer.sh'], shell=True)
            subprocess.run(['./scripts/start_fuzzer.sh'], shell=True)
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
            print()  # Empty line for readability
        except Exception as e:
            print(f"monitor_event:error\nerror_message:{str(e)}")
            self.reset_state()


def main():
    monitor = FuzzerMonitor()
    while True:
        monitor.monitor_cycle()
        time.sleep(monitor.INTERVAL)


if __name__ == "__main__":
    main()