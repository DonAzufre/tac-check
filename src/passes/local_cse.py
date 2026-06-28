from __future__ import annotations

from copy import deepcopy

from ..tac.ir import (
    BasicBlock,
    BinOpInst,
    Const,
    CopyInst,
    Function,
    Instruction,
    Param,
    Var,
)


class _ExprKey:
    def __init__(self, op: str, left: str, right: str):
        self.op = op
        self.pair = frozenset([left, right]) if op in ("add", "mul") else (left, right)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ExprKey):
            return NotImplemented
        return self.op == other.op and self.pair == other.pair

    def __hash__(self) -> int:
        return hash((self.op, self.pair))


def _operand_name(op) -> str | None:
    if isinstance(op, Const):
        return f"#{op.value}"
    if isinstance(op, Var):
        return op.name
    if isinstance(op, Param):
        return f"${op.name}"
    return None


def local_cse_block(block: BasicBlock) -> BasicBlock:
    avail: dict[_ExprKey, str] = {}
    new_insts: list[Instruction] = []
    for inst in block.instructions:
        if isinstance(inst, BinOpInst):
            left = _operand_name(inst.left)
            right = _operand_name(inst.right)
            if left is not None and right is not None:
                key = _ExprKey(inst.op, left, right)
                if key in avail:
                    new_insts.append(CopyInst(dst=inst.dst, src=Var(avail[key])))
                    continue
                avail[key] = inst.dst
        new_insts.append(inst)
    block.instructions = new_insts
    return block


def local_cse_function(func: Function, value_max: int = 7) -> Function:
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
        local_cse_block(new_block)
    return new_func
