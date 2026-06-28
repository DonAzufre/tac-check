from __future__ import annotations

from copy import deepcopy

from ..tac.cfg import reachable_labels
from ..tac.ir import (
    BasicBlock,
    BrInst,
    Const,
    ConstInst,
    Function,
    Instruction,
    JmpInst,
    Var,
)


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
    return new_func


def cfg_const_prop_function(func: Function, value_max: int = 7) -> Function:
    """Simple CFG-aware constant propagation without phi support."""
    from ..tac.cfg import topological_labels
    from ..tac.const_prop import _propagate_in_block, _substitute

    order = topological_labels(func)
    block_consts: dict[str, dict[str, int]] = {label: {} for label in func.blocks}

    changed = True
    for _ in range(len(func.blocks) * 2):
        if not changed:
            break
        changed = False
        for label in order:
            block = func.blocks[label]
            incoming: dict[str, int] = {}
            for pred in block.predecessors:
                for name, val in block_consts.get(pred, {}).items():
                    if name in incoming:
                        if incoming[name] != val:
                            del incoming[name]
                    else:
                        incoming[name] = val
            consts = dict(incoming)
            for inst in block.instructions:
                if isinstance(inst, ConstInst):
                    consts[inst.dst] = inst.value
                elif isinstance(inst, BrInst):
                    cond = _substitute(inst.cond, consts)
                    if isinstance(cond, Const):
                        # Branch folding will pick this up later
                        pass
                # other instructions update consts via dst not needed for propagation output
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
        _propagate_in_block(new_block)
    return new_func


def sccp_function(func: Function, value_max: int = 7) -> Function:
    from ..tac.cfg import reachable_labels

    TOP = object()
    UNDEF = object()
    values: dict[str, object] = {}
    reachable: set[str] = set()
    worklist: list[tuple[str, str | None]] = [(func.entry, None)]

    def get(v: str) -> object:
        return values.get(v, UNDEF)

    def set_val(v: str, val: object) -> bool:
        old = get(v)
        if old == TOP:
            return False
        if old == UNDEF:
            values[v] = val
            return True
        if old != val:
            values[v] = TOP
            return True
        return False

    while worklist:
        label, edge = worklist.pop(0)
        if label in reachable and edge is None:
            continue
        reachable.add(label)
        block = func.blocks[label]
        for inst in block.instructions:
            if isinstance(inst, ConstInst):
                if set_val(inst.dst, inst.value):
                    worklist.extend([(label, None)])
            elif isinstance(inst, BrInst) and isinstance(inst.cond, Const):
                target = inst.true_label if inst.cond.value != 0 else inst.false_label
                worklist.append((target, None))
            elif isinstance(inst, JmpInst):
                worklist.append((inst.label, None))

    opt = unreachable_elim_function(func, value_max)
    for label in list(opt.blocks.keys()):
        block = opt.blocks[label]
        new_insts: list[Instruction] = []
        for inst in block.instructions:
            if isinstance(inst, BrInst) and isinstance(inst.cond, Const):
                target = inst.true_label if inst.cond.value != 0 else inst.false_label
                new_insts.append(JmpInst(label=target))
            else:
                new_insts.append(inst)
        block.instructions = new_insts
    return opt
