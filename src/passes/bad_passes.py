from __future__ import annotations

from ..tac.ir import (
    BinOpInst,
    Const,
    ConstInst,
    Function,
    Param,
    Var,
)


def div_self_to_one_function(func: Function, value_max: int = 7) -> Function:
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
        for inst in block.instructions:
            if (
                isinstance(inst, BinOpInst)
                and inst.op == "div"
                and isinstance(inst.left, (Var, Param))
                and isinstance(inst.right, (Var, Param))
                and inst.left.name == inst.right.name
            ):
                new_block.instructions.append(ConstInst(dst=inst.dst, value=1))
            else:
                new_block.instructions.append(inst)
    return new_func


def drop_ret_deps_function(func: Function, value_max: int = 7) -> Function:
    """Deliberately drop every instruction before ret."""
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
        ret = None
        for inst in block.instructions:
            if isinstance(inst, RetInst):
                ret = inst
        if ret is not None:
            new_block.instructions.append(ConstInst(dst="__dummy", value=0))
            new_block.instructions.append(ret)
    return new_func


from ..tac.ir import RetInst
