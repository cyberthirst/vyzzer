import json
from bson import ObjectId
import os

from fuzz.helpers.db import get_mongo_client


def dump_verification_results(host=None, port=None):
    db = get_mongo_client(host, port)

    verification_results = db['verification_results']
    compilation_log = db['compilation_log']
    run_results = db['run_results']

    # Get all handled results
    handled_results = run_results.find({"is_handled": True})

    for result in handled_results:
        generation_id = result['generation_id']

        # Get the original contract from compilation log
        contract_data = compilation_log.find_one({"_id": ObjectId(generation_id)})
        if not contract_data:
            continue

        # Get verification results for this generation
        ver_result = verification_results.find_one({"generation_id": generation_id})
        if not ver_result:
            continue

        # Prepare output data
        output_data = {
            "generation_id": generation_id,
            "contract_code": contract_data.get("generation_result", ""),
            "function_inputs": contract_data.get("function_input_values", ""),
            "compilation_results": {},
            "verification_results": ver_result["results"]
        }

        # Add compilation results from all compilers
        for compiler_key in [k for k in result.keys() if k.startswith('result_')]:
            output_data["compilation_results"][compiler_key] = result[compiler_key]

        # Write to file in results directory
        results_dir = './results'
        filename = os.path.join(results_dir, f"verification_{generation_id}.json")
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)


if __name__ == "__main__":
    dump_verification_results()