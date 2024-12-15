from bson import ObjectId
from vyper.exceptions import StaticAssertionException

from fuzz.helpers.db import get_mongo_client


def print_contracts_with_compile_error(host=None, port=None):
    db = get_mongo_client(host, port)
    compilation_log = db['compilation_log']

    # Direct query for documents with non-null error_type
    contracts_with_errors = compilation_log.find({"error_type": {"$ne": None}})

    for contract_data in contracts_with_errors:
        if contract_data['error_message'].find('This is an unhandled') != -1:
            print("======================================================")
            print(f"error_message:\n{contract_data['error_message']}")

if __name__ == "__main__":
    print_contracts_with_compile_error()
