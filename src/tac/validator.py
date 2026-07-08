from __future__ import annotations

from .ir import (
    BasicBlock,
    BinOpInst,
    BrInst,
    CmpInst,
    Function,
    Instruction,
    JmpInst,
    LabelInst,
    NegInst,
    Param,
    RetInst,
    Var,
)


class ValidationError(Exception):
    """Raised when a parsed TAC function is structurally invalid."""


def _used_vars(inst: Instruction) -> set[str]:
    used: set[str] = set()
    for attr in ("src", "left", "right", "cond"):
        value = getattr(inst, attr, None)
        if isinstance(value, Var):
            used.add(value.name)
    return used


def _used_params(inst: Instruction) -> set[str]:
    used: set[str] = set()
    for attr in ("src", "left", "right", "cond"):
        value = getattr(inst, attr, None)
        if isinstance(value, Param):
            used.add(value.name)
    return used


def _dst(inst: Instruction) -> str | None:
    return getattr(inst, "dst", None)


def _check_terminator_position(label: str, block: BasicBlock) -> None:
    for idx, inst in enumerate(block.instructions[:-1]):
        if isinstance(inst, (RetInst, JmpInst, BrInst)):
            raise ValidationError(
                f"block '{label}' has instruction after terminator at position {idx}"
            )


def _check_successors(func: Function) -> None:
    for label, block in func.blocks.items():
        for succ in block.successors:
            if succ not in func.blocks:
                raise ValidationError(f"block '{label}' jumps to undefined label '{succ}'")
        for inst in block.instructions:
            if isinstance(inst, LabelInst) and inst.name != label:
                raise ValidationError(
                    f"block '{label}' contains mismatched label instruction '{inst.name}'"
                )
            if isinstance(inst, JmpInst) and inst.label not in func.blocks:
                raise ValidationError(f"jmp targets undefined label '{inst.label}'")
            if isinstance(inst, BrInst):
                for target in (inst.true_label, inst.false_label):
                    if target not in func.blocks:
                        raise ValidationError(f"br targets undefined label '{target}'")


def _meet_defs(pred_defs: list[set[str]]) -> set[str]:
    if not pred_defs:
        return set()
    result = set(pred_defs[0])
    for defs in pred_defs[1:]:
        result &= defs
    return result


def _check_defined_before_use(func: Function) -> None:
    params = set(func.param_names())
    out_defs: dict[str, set[str]] = {label: set(params) for label in func.blocks}

    order = func.ordered_block_labels()
    for _ in range(max(1, len(order) * 2)):
        changed = False
        for label in order:
            block = func.blocks[label]
            if label == func.entry:
                current = set(params)
            elif block.predecessors:
                current = _meet_defs([out_defs[p] for p in block.predecessors])
            else:
                current = set(params)

            for inst in block.instructions:
                unknown_params = _used_params(inst) - params
                if unknown_params:
                    names = ", ".join(sorted(unknown_params))
                    raise ValidationError(f"unknown parameter(s) used in block '{label}': {names}")
                missing = _used_vars(inst) - current
                if missing:
                    names = ", ".join(sorted(missing))
                    raise ValidationError(
                        f"variable(s) used before definition in block '{label}': {names}"
                    )
                dst = _dst(inst)
                if dst is not None:
                    current.add(dst)

            if current != out_defs[label]:
                out_defs[label] = current
                changed = True
        if not changed:
            break


def validate_function(func: Function) -> None:
    if not func.entry:
        raise ValidationError("function has no entry block")
    if func.entry not in func.blocks:
        raise ValidationError(f"entry block '{func.entry}' is missing")
    if len(set(func.param_names())) != len(func.params):
        raise ValidationError("duplicate parameter name")

    for label, block in func.blocks.items():
        if not label:
            raise ValidationError("empty label name")
        _check_terminator_position(label, block)

    _check_successors(func)
    _check_defined_before_use(func)
