from typing import List, Iterable

from types_d.base import BaseType


class Function:
    def __init__(
            self,
            name: str,
            mutability: int,
            visibility: str,
            input_parameters: List[BaseType],
            output_parameters: List[BaseType]
    ):
        self.name = name
        self.mutability = mutability
        self.visibility = visibility
        self.input_parameters = input_parameters
        self.output_parameters = output_parameters
        self._body = ""
        self._function_calls = []

    def render_call(self, input_parameters: Iterable[str]):
        return f"{self.name}({', '.join(input_parameters)})"

    def render_signature(self, input_parameters: Iterable[str]):
        output = ""
        if len(self.output_parameters) > 0:
            output = ", ".join(o.vyper_type for o in self.output_parameters)
            if len(self.output_parameters) > 1:
                output = f" -> ({output})"
            else:
                output = f" -> {output}"
        signature = f"def {self.name}({', '.join(f'{n}: {t}' for n, t in zip(input_parameters, self.input_parameters))}){output}:"
        return signature

    def render_definition(self, input_parameters: Iterable[str]):
        signature = self.render_signature(input_parameters)
        body = self._body.format(f.render_call(input_parameters) for f in self._function_calls)
        definition = f"{signature}\n{body}"
        return definition


class FuncTracker:
    def __init__(self):
        self._id = -1
        self._functions = []

    def __getitem__(self, item):
        return self._functions[item]

    def register_function(
            self,
            name,
            mutability,
            visibility,
            input_parameters,
            output_parameters
    ):
        # TODO: add `self.` the prefix to the name if `visibility` is `external`
        func = Function(name, mutability, visibility, input_parameters, output_parameters)
        self._functions.append(func)
        self._id = len(self._functions) - 1

    def find_functions_by_output(self, output_parameter: BaseType):
        functions = []
        for func in self._functions:
            if output_parameter in func.output_parameters:
                functions.append((func, func.output_parameters.index(output_parameter)))
        return functions

    @property
    def current_id(self):
        return self._id

    @property
    def next_id(self):
        return self._id + 1
