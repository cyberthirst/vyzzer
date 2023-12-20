from types_d.base import BaseType


class VarTracker:
    GLOBAL_KEY = "__global__"
    FUNCTION_KEY = "__function__"

    def __init__(self):
        self._var_id = 0
        self._vars = {
            self.GLOBAL_KEY: {},
            self.FUNCTION_KEY: {}
        }

    @property
    def next_id(self) -> int:
        return self._var_id + 1

    @property
    def current_id(self) -> int:
        return self._var_id

    def register_function_variable(self, name, level, var_type: BaseType):
        if var_type.vyper_type not in self._vars[self.FUNCTION_KEY]:
            self._vars[self.FUNCTION_KEY][var_type.vyper_type] = {
                level: []
            }
        if level not in self._vars[self.FUNCTION_KEY][var_type.vyper_type]:
            self._vars[self.FUNCTION_KEY][var_type.vyper_type][level] = []

        # TODO: check if a variable already exist
        self._vars[var_type.vyper_type][self.FUNCTION_KEY][level].append(name)
        self._var_id += 1

    def register_global_variable(self, name, var_type: BaseType):
        if var_type.vyper_type not in self._vars[self.GLOBAL_KEY]:
            self._vars[self.GLOBAL_KEY][var_type.vyper_type] = []
        # TODO: check if a variable already exist
        self._vars[self.GLOBAL_KEY][var_type.vyper_type].append(name)
        self._var_id += 1

    def remove_function_level(self, level: int):
        for vyper_type in self._vars[self.FUNCTION_KEY]:
            if level not in self._vars[self.GLOBAL_KEY][vyper_type]:
                continue
            self._var_id -= len(self._vars[self.GLOBAL_KEY][level])
            self._vars[self.GLOBAL_KEY][level] = []
