import os
from runner_api import RunnerBase
import json
import boa
from fuzz.helpers.json_encoders import ExtendedEncoder, ExtendedDecoder

# Override class methods

class RunnerNagini(RunnerBase):
    def generation_result(self):
        return f"generation_result_{self.compiler_key}"

    def init_compiler_settings(self):
        if self.compiler_key == "nagini":
            RunnerBase.init_compiler_settings(self)
            return

    def execution_result(self, _contract, fn, _input_values, internal=False):
        try:
            self.logger.debug("calling %s with calldata: %s", fn, _input_values)
            if internal:
                pass
            else:
                _, res = getattr(_contract, fn)(*_input_values)
            self.logger.debug("%s result: %s", fn, res)
            dump = _contract._storage.dump()
            _function_call_res = dict(state = dump, return_value = json.dumps(res, cls = ExtendedEncoder))
        except Exception as e:
            res = str(e)
            self.logger.debug("%stattr(_contract.internal, fn)(*_input_values) caught error: %s", fn, res)
            _function_call_res = dict(runtime_error=res)
        return _function_call_res


runner = RunnerNagini()

runner.start_runner()
