from __future__ import annotations

from copy import deepcopy

from ..tac.ir import (
    BasicBlock,
    BinOpInst,
    BrInst,
    Function,
    Instruction,
    JmpInst,
    LabelInst,
    RetInst,
)


def _may_trap(inst: Instruction) -> bool:
    if isinstance(inst, BinOpInst) and inst.op in ("div", "mod"):
        return True
    return False


def _used_vars(inst: Instruction) -> set[str]:
    used: set[str] = set()
    for attr in ("src", "left", "right", "cond"):
        val = getattr(inst, attr, None)
        if val is None:
            continue
        from ..tac.ir import Var

        if isinstance(val, Var):
            used.add(val.name)
    return used


def _dst_var(inst: Instruction) -> str | None:
    return getattr(inst, "dst", None)


def dce_block(block: BasicBlock) -> BasicBlock:
    live: set[str] = set()
    new_insts: list[Instruction] = []
    for inst in reversed(block.instructions):
        if isinstance(inst, RetInst):
            new_insts.append(inst)
            live.update(_used_vars(inst))
            continue
        if isinstance(inst, (JmpInst, BrInst, LabelInst)):
            new_insts.append(inst)
            if isinstance(inst, BrInst):
                live.update(_used_vars(inst))
            continue
        if _may_trap(inst):
            new_insts.append(inst)
            live.update(_used_vars(inst))
            live.discard(_dst_var(inst))
            continue
        dst = _dst_var(inst)
        if dst is not None and dst not in live:
            continue
        new_insts.append(inst)
        live.update(_used_vars(inst))
        if dst is not None:
            live.discard(dst)
    block.instructions = list(reversed(new_insts))
    return block


def dce_function(func: Function, value_max: int = 7) -> Function:
    new_func = Function(
        name=func.name,
        params=func.params,
        ret_ty=func.ret_ty,
        entry=func.entry,
        blocks={label: BasicBlock(label=label) for label in func.blocks},
    )
    for label, block in func.blocks.items():
        new_block = new_func.blocks[label]
        new_block.predecessors = list(block.predecessors)
        new_block.successors = list(block.successors)
        new_block.instructions = deepcopy(block.instructions)
        dce_block(new_block)
    return new_func
