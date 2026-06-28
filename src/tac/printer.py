from __future__ import annotations

from .ir import (
    BasicBlock,
    BinOpInst,
    BrInst,
    CmpInst,
    ConstInst,
    CopyInst,
    Function,
    Instruction,
    JmpInst,
    LabelInst,
    NegInst,
    Program,
    RetInst,
)


def print_operand(op) -> str:
    return str(op)


def print_instruction(inst: Instruction) -> str:
    if isinstance(inst, ConstInst):
        return f"{inst.dst} = const {inst.value}"
    if isinstance(inst, CopyInst):
        return f"{inst.dst} = copy {print_operand(inst.src)}"
    if isinstance(inst, BinOpInst):
        return f"{inst.dst} = {inst.op} {print_operand(inst.left)}, {print_operand(inst.right)}"
    if isinstance(inst, NegInst):
        return f"{inst.dst} = neg {print_operand(inst.src)}"
    if isinstance(inst, CmpInst):
        return f"{inst.dst} = {inst.op} {print_operand(inst.left)}, {print_operand(inst.right)}"
    if isinstance(inst, RetInst):
        return f"ret {print_operand(inst.src)}"
    if isinstance(inst, JmpInst):
        return f"jmp {inst.label}"
    if isinstance(inst, BrInst):
        return f"br {print_operand(inst.cond)}, {inst.true_label}, {inst.false_label}"
    if isinstance(inst, LabelInst):
        return f"{inst.name}:"
    return str(inst)


def print_block(block: BasicBlock, indent: str = "  ") -> str:
    lines: list[str] = []
    has_label = False
    for inst in block.instructions:
        if isinstance(inst, LabelInst):
            lines.append(f"{inst.name}:")
            has_label = True
        else:
            prefix = indent if has_label or block.label != "entry" else "  "
            lines.append(f"{prefix}{print_instruction(inst)}")
    return "\n".join(lines)


def print_function(func: Function) -> str:
    params = ", ".join(f"{ty} {name}" for name, ty in func.params)
    lines = [f"func {func.name}({params}) -> {func.ret_ty}"]
    for block in func.ordered_blocks():
        block_text = print_block(block)
        if block_text:
            lines.append(block_text)
    lines.append("end")
    return "\n".join(lines)


def print_program(program: Program) -> str:
    return print_function(program.function)
