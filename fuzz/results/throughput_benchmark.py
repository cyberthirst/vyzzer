from bson import ObjectId
import subprocess
import time

from fuzz.helpers.db import get_mongo_client

class Bench:
    def __init__(self, host=None, port=None):
        self.set_state(host, port)

    def print_seed(self):
        with open('logs/generator.log', 'r') as file:
            while True:
                has_50_lines = len(file.readlines()) >= 50
                if has_50_lines:
                    file.seek(0)
                    break
                file.seek(0)
                time.sleep(5)

            lines = [next(file) for _ in range(50)]
            for line in lines:
                if "Seed" in line:
                    self.seed = int(line.split("Seed: ")[1])
                    print(self.seed)
                    break

    def set_state(self, host=None, port=None):
        self.db = get_mongo_client(host, port)
        self.compilation_log = self.db['compilation_log']
        self.run_results = self.db['run_results']
        # set counts to 1 to avoid triggering error detection
        # in the first run
        self.generated_count = 1
        self.compiler_error_count = 1
        self.nagini_count = 1
        self.adder_count = 1
        self.verified_count = 1
        self.time = 0
        self.generator_errors = 0
        self.runner_errors = 0
        self.INTERVAL = 60
        self.seed = ''
        self.print_seed()

    def print_throughput(self):
        compilation_log = self.db['compilation_log']
        run_results = self.db['run_results']

        generated_count = compilation_log.count_documents({})
        compiler_error_count = compilation_log.count_documents({"error_type": {"$ne": None}})
        nagini_count = run_results.count_documents({"result_nagini": {"$exists": True}})
        adder_count = run_results.count_documents({"result_adder": {"$exists": True}})
        verified_count = run_results.count_documents({"is_handled": True})

        diff_generated = generated_count - self.generated_count
        diff_compiler_errors = compiler_error_count - self.compiler_error_count
        diff_nagini = nagini_count - self.nagini_count
        diff_adder = adder_count - self.adder_count
        diff_verified = verified_count - self.verified_count

        print(f"Diff_generated_contracts:{diff_generated}")
        print(f"Diff_compilation_errors:{diff_compiler_errors}")
        print(f"Diff_nagini_runs:{diff_nagini}")
        print(f"Diff_adder_runs:{diff_adder}")
        print(f"Diff_verified_results:{diff_verified}")

        self.generated_count = generated_count
        self.compiler_error_count = compiler_error_count
        self.nagini_count = nagini_count
        self.adder_count = adder_count
        self.verified_count = verified_count

        print(f"Total_generated_contracts:{self.generated_count}")
        print(f"Total_compilation_errors:{self.compiler_error_count}")
        print(f"Total_nagini_runs:{self.nagini_count}")
        print(f"Total_adder_runs:{self.adder_count}")
        print(f"Total_verified_results:{self.verified_count}")

        self.print_contracts_with_compile_error()
        self.print_contract_with_output_difference()

        print("\n")

        # runners either stopped working or 5 mins passed so we should free RAM
        if diff_nagini == 0 or diff_adder == 0 or self.time % 300 == 0:
            subprocess.run(['./scripts/kill_runners.sh'], shell=True)
            subprocess.run(['./scripts/run_runners.sh'], shell=True)
            self.runner_errors += 1
        else:
            self.runner_errors = 0

        if diff_generated == 0:
            # generator doesn't stall, but crashes - no need to restart
            subprocess.run(['./scripts/run_generator.sh'], shell=True)
            self.generator_errors += 1
        else:
            self.generator_errors = 0

        # restarting individual services didn't help, restart the whole fuzzer
        if self.runner_errors == 2 or self.generator_errors == 2:
            subprocess.run(['./scripts/kill_fuzzer.sh'], shell=True)
            subprocess.run(['./scripts/start_fuzzer.sh'], shell=True)
            pass

    def print_time(self):
        print(f"Time: {self.time}")
        self.time += self.INTERVAL

    def print_contracts_with_compile_error(self):
        compilation_log = self.db['compilation_log']

        with open('logs/compiler_crash.txt', 'a') as f:
            contracts_with_errors = compilation_log.find({"error_type": {"$ne": None}})

            for contract_data in contracts_with_errors:
                if contract_data['error_message'].find('This is an unhandled') != -1:
                    f.write(f"seed:{self.seed}\n")
                    f.write("Compiler crash")
                    f.write(f"error_message:\n{contract_data['error_message']}")
                    f.write("==========================================")

    def print_contract_with_output_difference(self):
        verification_results = self.db['verification_results']
        compilation_log = self.db['compilation_log']

        with open('logs/output_diff.txt', 'a') as f:
            # Direct query for verification results with non-null Storage or Return_Value
            interesting_results = verification_results.find({
                "results": {
                    "$elemMatch": {
                        "$or": [
                            {"results.Storage": {"$ne": None}},
                            {"results.Return_Value": {"$ne": None}}
                        ]
                    }
                }
            })

            for ver_result in interesting_results:
                f.write(f"seed:{self.seed}\n")
                f.write("Verification discrepancy:\n")
                f.write(str(ver_result['results']) + "\n")

                # Get and print the original contract
                contract_data = compilation_log.find_one({"_id": ObjectId(ver_result['generation_id'])})
                f.write("\nOriginal Contract:\n")
                f.write(contract_data['generation_result_nagini'] + "\n")
                f.write("===================================\n")


if __name__ == "__main__":
    bench = Bench()
    while True:
        bench.print_time()
        bench.print_throughput()
        time.sleep(bench.INTERVAL)