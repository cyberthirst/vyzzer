from bson import ObjectId
from fuzz.helpers.db import get_mongo_client


def print_handled_contracts(host=None, port=None):
    db = get_mongo_client(host, port)
    verification_results = db['verification_results']
    compilation_log = db['compilation_log']

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
        print("======================================================")
        print("Verification Result:")
        print(ver_result['results'])

        # Get and print the original contract
        contract_data = compilation_log.find_one({"_id": ObjectId(ver_result['generation_id'])})
        print("\nOriginal Contract:")
        print(contract_data['generation_result_nagini'])


if __name__ == "__main__":
    print_handled_contracts()