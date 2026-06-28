from __future__ import annotations

from dataclasses import dataclass

from .ir import (
    BinOpInst,
    BrInst,
    CmpInst,
    Const,
    ConstInst,
    CopyInst,
    Function,
    Instruction,
    JmpInst,
    LabelInst,
    NegInst,
    Operand,
    Param,
    Program,
    RetInst,
    Var,
)


@dataclass
class InterpretResult:
    done: bool
    trap: bool
    out: int | None
    steps: int
    timeout: bool


def _resolve(op: Operand, env: dict[str, int], params: dict[str, int]) -> int:
    if isinstance(op, Const):
        return op.value
    if isinstance(op, Param):
        return params[op.name]
    if isinstance(op, Var):
        return env[op.name]
    raise ValueError(f"unknown operand {op}")


def _eval_binop(op: str, left: int, right: int, mod: int) -> tuple[int, bool]:
    if op == "add":
        return (left + right) % mod, False
    if op == "sub":
        return (left - right) % mod, False
    if op == "mul":
        return (left * right) % mod, False
    if op == "div":
        if right == 0:
            return 0, True
        return left // right, False
    if op == "mod":
        if right == 0:
            return 0, True
        return left % right, False
    raise ValueError(f"unknown binop {op}")


def _eval_cmp(op: str, left: int, right: int, mod: int) -> int:
    if op == "eq":
        return 1 if left == right else 0
    if op == "lt":
        return 1 if left < right else 0
    raise ValueError(f"unknown cmp {op}")


def _execute_inst(
    inst: Instruction,
    env: dict[str, int],
    params: dict[str, int],
    mod: int,
) -> tuple[dict[str, int], bool]:
    trap = False
    if isinstance(inst, ConstInst):
        env[inst.dst] = inst.value
    elif isinstance(inst, CopyInst):
        env[inst.dst] = _resolve(inst.src, env, params)
    elif isinstance(inst, BinOpInst):
        left = _resolve(inst.left, env, params)
        right = _resolve(inst.right, env, params)
        val, trap = _eval_binop(inst.op, left, right, mod)
        if not trap:
            env[inst.dst] = val
    elif isinstance(inst, NegInst):
        env[inst.dst] = (-_resolve(inst.src, env, params)) % mod
    elif isinstance(inst, CmpInst):
        left = _resolve(inst.left, env, params)
        right = _resolve(inst.right, env, params)
        env[inst.dst] = _eval_cmp(inst.op, left, right, mod)
    elif isinstance(inst, (RetInst, JmpInst, BrInst, LabelInst)):
        pass
    return env, trap


def run_function(
    func: Function,
    inputs: dict[str, int],
    value_max: int = 7,
    max_steps: int = 128,
) -> InterpretResult:
    mod = value_max + 1
    params = {name: inputs[name] for name in func.param_names()}
    flat, label_map = func.flatten_instructions()
    env: dict[str, int] = {}
    pc = 0
    out: int | None = None
    steps = 0
    done = False
    trap = False
    while steps < max_steps:
        if pc >= len(flat):
            break
        idx, inst, block_label = flat[pc]
        env, trap_local = _execute_inst(inst, env, params, mod)
        steps += 1
        if trap_local:
            trap = True
            break
        if isinstance(inst, RetInst):
            out = _resolve(inst.src, env, params)
            done = True
            break
        if isinstance(inst, JmpInst):
            pc = label_map[inst.label]
            continue
        if isinstance(inst, BrInst):
            cond = _resolve(inst.cond, env, params)
            target = inst.true_label if cond != 0 else inst.false_label
            pc = label_map[target]
            continue
        pc += 1
    return InterpretResult(
        done=done,
        trap=trap,
        out=out,
        steps=steps,
        timeout=not done and not trap and steps >= max_steps,
    )


def run(
    program: Program,
    inputs: dict[str, int],
    value_max: int = 7,
    max_steps: int = 128,
) -> InterpretResult:
    return run_function(program.function, inputs, value_max, max_steps)
