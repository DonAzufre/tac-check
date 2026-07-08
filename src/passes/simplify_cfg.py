from __future__ import annotations

from copy import deepcopy

from ..tac.cfg import reachable_labels
from ..tac.ir import (
    BasicBlock,
    BinOpInst,
    BrInst,
    CmpInst,
    Const,
    ConstInst,
    CopyInst,
    Function,
    Instruction,
    JmpInst,
    NegInst,
    Param,
    Var,
)
from .const_fold import _eval_const_binop


def unreachable_elim_function(func: Function, value_max: int = 7) -> Function:
    reachable = reachable_labels(func)
    new_func = Function(
        name=func.name,
        params=func.params,
        ret_ty=func.ret_ty,
        entry=func.entry,
        blocks={label: BasicBlock(label=label) for label in func.blocks if label in reachable},
    )
    for label, block in func.blocks.items():
        if label not in reachable:
            continue
        new_block = new_func.blocks[label]
        new_block.instructions = deepcopy(block.instructions)
        new_block.predecessors = [p for p in block.predecessors if p in reachable]
        new_block.successors = [s for s in block.successors if s in reachable]
    return new_func


def branch_fold_function(func: Function, value_max: int = 7) -> Function:
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
        new_insts: list[Instruction] = []
        for inst in block.instructions:
            if isinstance(inst, BrInst) and isinstance(inst.cond, Const):
                target = inst.true_label if inst.cond.value != 0 else inst.false_label
                new_insts.append(JmpInst(label=target))
                new_block.successors = [target]
                continue
            new_insts.append(deepcopy(inst))
        new_block.instructions = new_insts
    return _recompute_edges(new_func)


def _recompute_edges(func: Function) -> Function:
    labels = list(func.blocks.keys())
    for block in func.blocks.values():
        block.successors = []
        block.predecessors = []
    for label in labels:
        block = func.blocks[label]
        term = block.terminator()
        if term is None:
            idx = labels.index(label)
            if idx + 1 < len(labels):
                block.successors.append(labels[idx + 1])
        elif isinstance(term, JmpInst):
            block.successors.append(term.label)
        elif isinstance(term, BrInst):
            block.successors.extend([term.true_label, term.false_label])
    for label, block in func.blocks.items():
        block.successors = [s for s in block.successors if s in func.blocks]
        for succ in block.successors:
            func.blocks[succ].predecessors.append(label)
    return func


def _operand_const(op, consts: dict[str, int]) -> int | None:
    if isinstance(op, Const):
        return op.value
    if isinstance(op, Var):
        return consts.get(op.name)
    return None


def _substitute(op, consts: dict[str, int]):
    val = _operand_const(op, consts)
    if val is not None:
        return Const(val)
    return op


def _meet(pred_maps: list[dict[str, int]]) -> dict[str, int]:
    if not pred_maps:
        return {}
    keys = set(pred_maps[0])
    for mapping in pred_maps[1:]:
        keys &= set(mapping)
    result: dict[str, int] = {}
    for key in keys:
        vals = {mapping[key] for mapping in pred_maps}
        if len(vals) == 1:
            result[key] = vals.pop()
    return result


def _transfer_inst(inst: Instruction, consts: dict[str, int], mod: int) -> Instruction:
    if isinstance(inst, ConstInst):
        consts[inst.dst] = inst.value
        return deepcopy(inst)
    if isinstance(inst, CopyInst):
        src = _substitute(inst.src, consts)
        if isinstance(src, Const):
            consts[inst.dst] = src.value
            return ConstInst(dst=inst.dst, value=src.value)
        consts.pop(inst.dst, None)
        return CopyInst(dst=inst.dst, src=src)
    if isinstance(inst, BinOpInst):
        left = _substitute(inst.left, consts)
        right = _substitute(inst.right, consts)
        left_val = _operand_const(left, consts)
        right_val = _operand_const(right, consts)
        if left_val is not None and right_val is not None:
            folded = _eval_const_binop(inst.op, left_val, right_val, mod)
            if folded is not None:
                consts[inst.dst] = folded
                return ConstInst(dst=inst.dst, value=folded)
        consts.pop(inst.dst, None)
        return BinOpInst(dst=inst.dst, op=inst.op, left=left, right=right)
    if isinstance(inst, NegInst):
        src = _substitute(inst.src, consts)
        src_val = _operand_const(src, consts)
        if src_val is not None:
            folded = (-src_val) % mod
            consts[inst.dst] = folded
            return ConstInst(dst=inst.dst, value=folded)
        consts.pop(inst.dst, None)
        return NegInst(dst=inst.dst, src=src)
    if isinstance(inst, CmpInst):
        left = _substitute(inst.left, consts)
        right = _substitute(inst.right, consts)
        left_val = _operand_const(left, consts)
        right_val = _operand_const(right, consts)
        if left_val is not None and right_val is not None:
            if inst.op == "eq":
                folded = 1 if left_val == right_val else 0
            elif inst.op == "lt":
                folded = 1 if left_val < right_val else 0
            else:
                folded = None
            if folded is not None:
                consts[inst.dst] = folded
                return ConstInst(dst=inst.dst, value=folded)
        consts.pop(inst.dst, None)
        return CmpInst(dst=inst.dst, op=inst.op, left=left, right=right)
    if isinstance(inst, BrInst):
        return BrInst(
            cond=_substitute(inst.cond, consts),
            true_label=inst.true_label,
            false_label=inst.false_label,
        )
    return deepcopy(inst)


def _transfer_block(block: BasicBlock, incoming: dict[str, int], mod: int) -> tuple[list[Instruction], dict[str, int]]:
    consts = dict(incoming)
    new_insts: list[Instruction] = []
    for inst in block.instructions:
        new_insts.append(_transfer_inst(inst, consts, mod))
    return new_insts, consts


def cfg_const_prop_function(func: Function, value_max: int = 7) -> Function:
    """CFG-aware constant propagation using a must-constant meet over predecessors."""
    mod = value_max + 1
    order = func.ordered_block_labels()
    in_maps: dict[str, dict[str, int]] = {label: {} for label in func.blocks}
    out_maps: dict[str, dict[str, int]] = {label: {} for label in func.blocks}

    for _ in range(max(1, len(order) * 4)):
        changed = False
        for label in order:
            block = func.blocks[label]
            if label == func.entry:
                incoming: dict[str, int] = {}
            elif block.predecessors:
                incoming = _meet([out_maps[p] for p in block.predecessors])
            else:
                incoming = {}
            _, outgoing = _transfer_block(block, incoming, mod)
            if incoming != in_maps[label] or outgoing != out_maps[label]:
                in_maps[label] = incoming
                out_maps[label] = outgoing
                changed = True
        if not changed:
            break

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
        new_block.instructions, _ = _transfer_block(block, in_maps[label], mod)
    return _recompute_edges(new_func)


def sccp_function(func: Function, value_max: int = 7) -> Function:
    """A conservative simplified SCCP-style pipeline.

    The original project intentionally keeps SCCP course-scale.  This implementation
    reuses the sound CFG constant propagation lattice, folds now-constant branches,
    and removes unreachable blocks.
    """
    propagated = cfg_const_prop_function(func, value_max)
    folded = branch_fold_function(propagated, value_max)
    return unreachable_elim_function(folded, value_max)
