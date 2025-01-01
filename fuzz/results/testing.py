from bson import ObjectId
from vyper.exceptions import StaticAssertionException

from fuzz.helpers.db import get_mongo_client

def print_contracts_with_compile_error(host=None, port=None):
    """
    runner_nagini:DEBUG:2024-12-17 12:29:50,520:Compiling contract id: 67615fea72f899962c7ea988
    runner_nagini:DEBUG:2024-12-17 12:29:50,520:Constructor values: []
    runner_nagini:DEBUG:2024-12-17 12:29:50,536:calling func_0 with calldata: [94, 255]
    """
    db = get_mongo_client(host, port)
    compilation_log = db['compilation_log']

    # =============================COMPILATION
    count = compilation_log.count_documents({})
    print(f"Total documents: {count}")
    count_error = compilation_log.count_documents({"error_type": {"$ne": None}})
    #cursor = compilation_log.find({"error_type": {"$ne": None}})
    #for doc in cursor:
    #    print(doc['error_type'])
    #    print(doc['error_message'])

    print(f"Total documents with error: {count_error}")
    # =============================COMPILATION-END

    # =============================RUNNERS
    run_results = db['run_results']
    handled_results = run_results.count_documents({"is_handled": True})
    print(f"Total verified results: {handled_results}")

    # ==============================
    contract_data = compilation_log.find_one({"_id": ObjectId('6772b3e502d3836300c77189')})
    print(contract_data['generation_result_adder'])

def print_all_runtime_errors(host=None, port=None):
    db = get_mongo_client(host, port)
    run_results = db['run_results']
    compilation_log = db['compilation_log']
    handled_results = run_results.find({"is_handled": True})
    for res in handled_results:
        if "assert not (value" in str(res['result_adder']):
            #print(res['result_adder'])
            print(res)
            contract_data = compilation_log.find_one({"_id": ObjectId('67751853d453bded01b3b426')})
            print(contract_data['generation_result_adder'])
            break
        #if res['runtime_error'] is not None:
        #    print(res['runtime_error'])


if __name__ == "__main__":
    #print_contracts_with_compile_error()
    print_all_runtime_errors()