from runner_api import RunnerBase
import json
from fuzz.helpers.json_encoders import ExtendedEncoder, ExtendedDecoder

# Override class methods

class RunnerNagini(RunnerBase):
    def generation_result(self):
        return f"generation_result_{self.compiler_key}"

    def init_compiler_settings(self):
        if self.compiler_key == "nagini":
            RunnerBase.init_compiler_settings(self)
            return

    # currently we're overriding the parent because we're dumping
    # the contract's storage via boa, not from the computation obj
    def execution_result(self, _contract, fn, _input_values, internal=False):
        try:
            self.logger.debug("calling %s with calldata: %s", fn, _input_values)
            # internal function calls are not yet enables in runner_api.py
            # so the if branch is currently never taken
            if internal:
                pass
            else:
                res = getattr(_contract, fn)(*_input_values)
            self.logger.debug("%s result: %s", fn, res)
            dump = _contract._storage.dump()
            _function_call_res = dict(state = dump, return_value = json.dumps(res, cls = ExtendedEncoder))
        except Exception as e:
            #res = str(e)
            res = str(e).encode('utf-8', 'replace').decode('utf-8')
            self.logger.debug("%stattr(_contract.internal, fn)(*_input_values) caught error: %s", fn, res)
            _function_call_res = dict(runtime_error=res)
        return _function_call_res


runner = RunnerNagini()

runner.start_runner()
