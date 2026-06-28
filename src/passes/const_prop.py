from __future__ import annotations

from copy import deepcopy

from ..tac.ir import (
    BasicBlock,
    BinOpInst,
    CmpInst,
    Const,
    ConstInst,
    CopyInst,
    Function,
    Instruction,
    NegInst,
    Operand,
    Var,
)


def _substitute(op: Operand, consts: dict[str, int]) -> Operand:
    if isinstance(op, Var) and op.name in consts:
        return Const(value=consts[op.name])
    return op


def _propagate_in_block(block: BasicBlock) -> BasicBlock:
    consts: dict[str, int] = {}
    new_insts: list[Instruction] = []
    for inst in block.instructions:
        new_inst: Instruction
        if isinstance(inst, ConstInst):
            consts[inst.dst] = inst.value
            new_inst = inst
        elif isinstance(inst, CopyInst):
            src = _substitute(inst.src, consts)
            if isinstance(src, Const):
                consts[inst.dst] = src.value
                new_inst = ConstInst(dst=inst.dst, value=src.value)
            else:
                new_inst = CopyInst(dst=inst.dst, src=src)
        elif isinstance(inst, BinOpInst):
            left = _substitute(inst.left, consts)
            right = _substitute(inst.right, consts)
            new_inst = BinOpInst(dst=inst.dst, op=inst.op, left=left, right=right)
        elif isinstance(inst, NegInst):
            src = _substitute(inst.src, consts)
            new_inst = NegInst(dst=inst.dst, src=src)
        elif isinstance(inst, CmpInst):
            left = _substitute(inst.left, consts)
            right = _substitute(inst.right, consts)
            new_inst = CmpInst(dst=inst.dst, op=inst.op, left=left, right=right)
        else:
            new_inst = deepcopy(inst)
        new_insts.append(new_inst)
    block.instructions = new_insts
    return block


def const_prop_function(func: Function, value_max: int = 7) -> Function:
    new_func = Function(
        name=func.name,
        params=func.params,
        ret_ty=func.ret_ty,
        entry=func.entry,
        blocks={label: block.__class__(label=block.label) for label, block in func.blocks.items()},
    )
    for label, block in func.blocks.items():
        new_block = new_func.blocks[label]
        new_block.predecessors = list(block.predecessors)
        new_block.successors = list(block.successors)
        new_block.instructions = list(block.instructions)
        _propagate_in_block(new_block)
    return new_func
