from bson import ObjectId
from vyper.exceptions import StaticAssertionException

from fuzz.helpers.db import get_mongo_client


def print_contracts_with_compile_error(host=None, port=None):
    db = get_mongo_client(host, port)
    compilation_log = db['compilation_log']

    # Direct query for documents with non-null error_type
    contracts_with_errors = compilation_log.find({"error_type": {"$ne": None}})

    for contract_data in contracts_with_errors:
        if contract_data['error_type'] == 'StaticAssertionException':
            continue
        if contract_data['error_message'].startswith('Value must be a literal integer, unless a bound is specified'):
            continue
        print("======================================================")
        print(f"error_type:\n{contract_data['error_type']}")
        print(f"error_message:\n{contract_data['error_message']}")
        print(f"contract_code:\n{contract_data['generation_result_nagini']}")

if __name__ == "__main__":
    print_contracts_with_compile_error()
