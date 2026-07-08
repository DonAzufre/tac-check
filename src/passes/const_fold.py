from __future__ import annotations

from ..tac.ir import (
    BinOpInst,
    BrInst,
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


def _eval_const_binop(op: str, left: int, right: int, mod: int) -> int | None:
    if op == "add":
        return (left + right) % mod
    if op == "sub":
        return (left - right) % mod
    if op == "mul":
        return (left * right) % mod
    if op == "div":
        if right == 0:
            return None
        return left // right
    if op == "mod":
        if right == 0:
            return None
        return left % right
    return None


def _is_const(op: Operand) -> bool:
    return isinstance(op, Const)


def _const_value(op: Operand) -> int:
    if isinstance(op, Const):
        return op.value
    raise ValueError("operand is not constant")


def const_fold_function(func: Function, value_max: int = 7) -> Function:
    mod = value_max + 1
    new_func = Function(
        name=func.name,
        params=func.params,
        ret_ty=func.ret_ty,
        entry=func.entry,
        blocks={label: block.__class__(label=block.label) for label, block in func.blocks.items()},
    )
    for label in func.ordered_block_labels():
        block = func.blocks[label]
        new_block = new_func.blocks[label]
        new_block.predecessors = list(block.predecessors)
        new_block.successors = list(block.successors)
        consts: dict[str, int] = {}
        for inst in block.instructions:
            new_inst = _fold_instruction(inst, mod, consts)
            _update_consts_after(new_inst, consts)
            new_block.instructions.append(new_inst)
    return new_func


def _operand_to_const(op, consts: dict[str, int]) -> int | None:
    if isinstance(op, Const):
        return op.value
    if isinstance(op, Var) and op.name in consts:
        return consts[op.name]
    return None


def _update_consts_after(inst: Instruction, consts: dict[str, int]) -> None:
    dst = getattr(inst, "dst", None)
    if dst is None:
        return
    if isinstance(inst, ConstInst):
        consts[dst] = inst.value
    elif isinstance(inst, CopyInst):
        src_val = _operand_to_const(inst.src, consts)
        if src_val is not None:
            consts[dst] = src_val
        else:
            consts.pop(dst, None)
    else:
        consts.pop(dst, None)


def _fold_instruction(inst: Instruction, mod: int, consts: dict[str, int]) -> Instruction:
    def to_const(op):
        return _operand_to_const(op, consts)

    if isinstance(inst, BinOpInst):
        left = to_const(inst.left)
        right = to_const(inst.right)
        if left is not None and right is not None:
            folded = _eval_const_binop(inst.op, left, right, mod)
            if folded is not None:
                return ConstInst(dst=inst.dst, value=folded)
        return BinOpInst(
            dst=inst.dst,
            op=inst.op,
            left=Const(left) if left is not None else inst.left,
            right=Const(right) if right is not None else inst.right,
        )
    if isinstance(inst, NegInst):
        v = to_const(inst.src)
        if v is not None:
            return ConstInst(dst=inst.dst, value=(-v) % mod)
        return NegInst(dst=inst.dst, src=inst.src)
    if isinstance(inst, CmpInst):
        left = to_const(inst.left)
        right = to_const(inst.right)
        if left is not None and right is not None:
            if inst.op == "eq":
                val = 1 if left == right else 0
            elif inst.op == "lt":
                val = 1 if left < right else 0
            else:
                return inst
            return ConstInst(dst=inst.dst, value=val)
        return CmpInst(
            dst=inst.dst,
            op=inst.op,
            left=Const(left) if left is not None else inst.left,
            right=Const(right) if right is not None else inst.right,
        )
    if isinstance(inst, CopyInst):
        v = to_const(inst.src)
        if v is not None:
            return ConstInst(dst=inst.dst, value=v)
        return CopyInst(dst=inst.dst, src=inst.src)
    if isinstance(inst, BrInst):
        v = to_const(inst.cond)
        if v is not None:
            return BrInst(cond=Const(v), true_label=inst.true_label, false_label=inst.false_label)
        return inst
    return inst
