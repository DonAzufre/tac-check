from __future__ import annotations

from itertools import product
from typing import Callable

from src.tac.interpreter import InterpretResult, run
from src.tac.ir import Function, Program
from src.tac.parser import parse_program


def result_observation(result: InterpretResult) -> tuple[bool, bool, int | None, bool]:
    return (result.done, result.trap, result.out, result.timeout)


def assert_equiv_on_finite_domain(
    source_text: str,
    optimize: Callable[[Function], Function],
    value_max: int = 7,
    max_steps: int = 64,
) -> None:
    source = parse_program(source_text, value_max=value_max)
    optimized = Program(function=optimize(source.function, value_max=value_max))
    params = source.function.param_names()
    for values in product(range(value_max + 1), repeat=len(params)):
        inputs = dict(zip(params, values))
        src_result = run(source, inputs, value_max=value_max, max_steps=max_steps)
        opt_result = run(optimized, inputs, value_max=value_max, max_steps=max_steps)
        assert result_observation(src_result) == result_observation(opt_result), (
            f"mismatch for inputs {inputs}: {src_result} != {opt_result}"
        )
