import json

from ivy.frontend.loader import loads
from ivy.frontend.env import Env
from runner_api import RunnerBase
from fuzz.helpers.json_encoders import ExtendedEncoder, ExtendedDecoder

# Override class methods

class RunnerDiff(RunnerBase):
    def generation_result(self):
        return f"generation_result_{self.compiler_key}"

    def init_compiler_settings(self):
        pass

    def _handle_compilation(self, _contract_desc, input_values, init_values):
        results = []
        for iv in init_values:
            self.logger.debug("Constructor values: %s", iv)
            try:
                contract = loads(_contract_desc[self.generation_result()],*iv)
            except Exception as e:
                self.logger.debug("Deployment failed: %s", str(e))
                results.append(dict(deploy_error=str(e)))
                continue

            _r = dict()
            externals = [c for c in dir(contract) if c.startswith('func')]
            for fn in externals:
                print("contract: ", contract)
                _r[fn] = [self.execution_result(contract, fn, input_values[fn][i])
                          for i in range(self.inputs_per_function)]
            
            print("smth works still\n")
            results.append(_r)
        Env().clear_state()
        return results
    

    def execution_result(self, _contract, fn, _input_values, internal=False):
        try:
            self.logger.debug("calling %s with calldata: %s", fn, _input_values)
            if internal:
               pass
            else:
                print("here: ", _contract)
                #computation, res = getattr(_contract, fn)(*_input_values)
                res = getattr(_contract, fn)(*_input_values)
                print("res: ", res)
                # in verifier
                #for v, k in dump.items():
                #    assert dump2[k] = v
            self.logger.debug("%s result: %s", fn, res)
            dump = _contract.storage_dump()
            _function_call_res = dict(state = dump, return_value = json.dumps(res, cls = ExtendedEncoder))
            print("here3\n")
        except Exception as e:
            #res = str(e)
            res = str(e).encode('utf-8', 'replace').decode('utf-8')
            self.logger.debug("%s caught error: %s", fn, res)
            _function_call_res = dict(runtime_error=res)
        return _function_call_res



runner = RunnerDiff()



runner.start_runner()
