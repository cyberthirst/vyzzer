
from fuzz.verifiers.verifier_api import VerifierBase, VerifierException
import time

import logging
from fuzz.helpers.db import get_mongo_client

class VerifierIvy (VerifierBase):
    # Add new verifiers to the mapping
    def verify_two_results(self, _res0, _res1):
        if self.RUNTIME_ERROR in _res0 or self.RUNTIME_ERROR in _res1:
            self.runtime_error_handler(_res0, _res1)
            return {}
        verifiers = {
            "Storage": (self.storage_verifier, (_res0["state"], _res1["state"])),
            #"Memory": (self.memory_verifier, (_res0["memory"], _res1["memory"])),
            #"Gas": (self.gas_verifier, (_res0["consumed_gas"], _res1["consumed_gas"])),
            "Return_Value": (self.return_value_verifier, (_res0["return_value"], _res1["return_value"]))
        }
        d = {}
        for name, (verifier, params) in verifiers.items():
            d[name] = self.verify_and_catch(verifier, params)
        return d

    # storagex are dicts mapping variable names to their decoded values
    def storage_verifier(self, storage0, storage1):
        if storage0 != storage1:
            raise VerifierException(f"Storage discrepancy: {storage0} | {storage1}")

    def compilation_error_handler(self, _res0, _res1):
        if not isinstance(_res0, str):
            return
        compilation_err_str = "This is an unhandled internal compiler error."
        if compilation_err_str in _res0:
            assert compilation_err_str in _res1
            raise VerifierException("This is an unhandled internal compiler error.")

verifier = VerifierIvy()

verifier.start_verifier()