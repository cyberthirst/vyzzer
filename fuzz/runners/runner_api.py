import json
import os
import logging

import pika.exceptions
import boa
from bson.objectid import ObjectId

from fuzz.helpers.config import Config
from fuzz.helpers.queue_managers import QueueManager
from fuzz.helpers.db import get_mongo_client
from fuzz.helpers.json_encoders import ExtendedEncoder, ExtendedDecoder


class RunnerBase:

    def __init__(self, config_file=None):
        self.conf = Config(config_file) if config_file is not None else Config()
        self.inputs_per_function = len(self.conf.input_strategies)
        self.init_config()
        self.init_logger()
        self.init_queue()
        self.init_compiler_settings()
        self.init_db()

    def start_runner(self):
        while True:
            try:
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(
                    self.queue_name, on_message_callback=self.callback)
                self.channel.start_consuming()
            except pika.exceptions.AMQPError:
                self.logger.info("AMQP error. Failing...")
                exit(1)

    def callback(self, ch, method, properties, body):
        data = json.loads(body)

        self.logger.debug("Compiling contract id: %s", data["_id"])

        result = self.handle_compilation(data)
        self.logger.debug("Compilation and execution result: %s", result)

        self.queue_collection.update_one({"_id": ObjectId(data["_id"])},
                                         {"$set": {f"compiled_{self.compiler_key}": True}})
        self.run_results_collection.update_one({"generation_id": data["_id"]},
                                               {"$set": {f"result_{self.compiler_key}": result, "is_handled": False}})
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def generation_result(self):
        return "generation_result"

    def handle_compilation(self, _contract_desc):
        input_values = json.loads(
            _contract_desc["function_input_values"], cls=ExtendedDecoder)
        init_values = input_values.get("__init__", [[]])

        results = []
        for iv in init_values:
            self.logger.debug("Constructor values: %s", iv)
            try:
                contract = boa.loads(_contract_desc[self.generation_result()],
                                     *iv, compiler_args=self.comp_settings)
            except Exception as e:
                self.logger.debug("Deployment failed: %s", str(e))
                results.append(dict(deploy_error=str(e)))
                continue

            _r = dict()
            externals = [c for c in dir(contract) if c.startswith('func')]
            internals = [c for c in dir(
                contract.internal) if c.startswith('func')]
            for fn in externals:
                function_call_res = []
                _r[fn] = [self.execution_result(contract, fn, input_values[fn][i])
                          for i in range(self.inputs_per_function)]
            """
            for fn in internals:
                function_call_res = []
                _r[fn] = [self.execution_result(
                    contract, fn, input_values[fn][i], internal=True)
                    for i in range(self.inputs_per_function)]
            
            fn = "__default__"
            if fn in dir(contract):
                function_call_res = [self.execution_result(contract, fn, [])
                                     for i in range(self.inputs_per_function)]
                _r[fn] = function_call_res
            """
            results.append(_r)
        boa.reset_env()
        return results

    def execution_result(self, _contract, fn, _input_values, internal=False):
        try:
            self.logger.debug("calling %s with calldata: %s", fn, _input_values)
            if internal:
                computation, res = getattr(_contract.internal, fn)(*_input_values)
            else:
                computation, res = getattr(_contract, fn)(*_input_values)
            self.logger.debug("%s result: %s", fn, res)
            _function_call_res = self.compose_result(_contract, computation, res)
        except Exception as e:
            res = str(e)
            self.logger.debug("%s caught error: %s", fn, res)
            _function_call_res = dict(runtime_error=res)
        return _function_call_res

    # add/remove the data
    def compose_result(self, _contract, comp, ret) -> dict:
        # now we dump first ten slots only
        state = [str(comp.state.get_storage(bytes.fromhex(
            _contract.address[2:]), i)) for i in range(10)]

        # first 1280 bytes are dumped
        memory = comp.memory_read_bytes(0, 1280).hex()

        consumed_gas = comp.get_gas_used()
        # The order of function calls is the same for all runners
        # Adding the name just to know what result is checked
        return dict(state=state, memory=memory, consumed_gas=consumed_gas,
                    return_value=json.dumps(ret, cls=ExtendedEncoder))

    def init_config(self):
        self.compiler_name = os.environ.get("SERVICE_NAME")
        self.compiler_params = self.conf.get_compiler_params_by_name(
            self.compiler_name)
        self.compiler_key = f"{self.compiler_name}"

    def init_logger(self):
        logger_level = getattr(logging, self.conf.verbosity)
        self.logger = logging.getLogger(f"runner_{self.compiler_key}")
        logging.basicConfig(
            format='%(name)s:%(levelname)s:%(asctime)s:%(message)s', level=logger_level)
        self.logger.info("Starting %s runner", self.compiler_key)

    def init_queue(self):
        self.queue_name = 'queue3.10'
        queue_params = self.conf.compiler_queues[self.compiler_params["queue"]]

        self.qm = QueueManager(queue_params["host"],
                               int(queue_params["port"]), self.queue_name, self.logger)
        self.channel = self.qm.channel

    # The boa interface might change
    def init_compiler_settings(self):
        self.comp_settings = {}
        if self.compiler_params["exec_params"].get(self.compiler_name, False):
            self.comp_settings["experimental_codegen"] = True

        if 'enable_decimals' in self.conf.extra_flags:
            self.comp_settings["enable_decimals"] = True

    def init_db(self):
        db_ = get_mongo_client(self.conf.db["host"], self.conf.db["port"])
        self.queue_collection = db_["compilation_log"]
        self.run_results_collection = db_["run_results"]
