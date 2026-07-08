from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

Op = Literal["add", "sub", "mul", "div", "mod"]
CmpOp = Literal["eq", "lt"]


@dataclass(frozen=True)
class Const:
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class Var:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Param:
    name: str

    def __str__(self) -> str:
        return self.name


Operand = Union[Const, Var, Param]


@dataclass
class Instruction:
    pass


@dataclass
class ConstInst(Instruction):
    dst: str
    value: int

    def __str__(self) -> str:
        return f"{self.dst} = const {self.value}"


@dataclass
class CopyInst(Instruction):
    dst: str
    src: Operand

    def __str__(self) -> str:
        return f"{self.dst} = copy {self.src}"


@dataclass
class BinOpInst(Instruction):
    dst: str
    op: Op
    left: Operand
    right: Operand

    def __str__(self) -> str:
        return f"{self.dst} = {self.op} {self.left}, {self.right}"


@dataclass
class NegInst(Instruction):
    dst: str
    src: Operand

    def __str__(self) -> str:
        return f"{self.dst} = neg {self.src}"


@dataclass
class CmpInst(Instruction):
    dst: str
    op: CmpOp
    left: Operand
    right: Operand

    def __str__(self) -> str:
        return f"{self.dst} = {self.op} {self.left}, {self.right}"


@dataclass
class RetInst(Instruction):
    src: Operand

    def __str__(self) -> str:
        return f"ret {self.src}"


@dataclass
class JmpInst(Instruction):
    label: str

    def __str__(self) -> str:
        return f"jmp {self.label}"


@dataclass
class BrInst(Instruction):
    cond: Operand
    true_label: str
    false_label: str

    def __str__(self) -> str:
        return f"br {self.cond}, {self.true_label}, {self.false_label}"


@dataclass
class LabelInst(Instruction):
    name: str

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass
class BasicBlock:
    label: str
    instructions: list[Instruction] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)
    predecessors: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.instructions) == 0

    def terminator(self) -> Instruction | None:
        if self.is_empty():
            return None
        last = self.instructions[-1]
        if isinstance(last, (RetInst, JmpInst, BrInst)):
            return last
        return None


@dataclass
class Function:
    name: str
    params: list[tuple[str, str]]
    ret_ty: str
    entry: str
    blocks: dict[str, BasicBlock] = field(default_factory=dict)

    def param_names(self) -> list[str]:
        return [p[0] for p in self.params]

    def ordered_blocks(self) -> list[BasicBlock]:
        return [self.blocks[label] for label in self.ordered_block_labels()]

    def ordered_block_labels(self) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def dfs(label: str) -> None:
            if label in visited or label not in self.blocks:
                return
            visited.add(label)
            order.append(label)
            for succ in self.blocks[label].successors:
                dfs(succ)

        dfs(self.entry)
        for label in self.blocks:
            if label not in visited:
                order.append(label)
        return order

    def flatten_instructions(self) -> tuple[list[tuple[int, Instruction, str]], dict[str, int]]:
        result: list[tuple[int, Instruction, str]] = []
        idx = 0
        label_map: dict[str, int] = {}
        for block in self.ordered_blocks():
            for inst in block.instructions:
                if isinstance(inst, LabelInst):
                    label_map[inst.name] = idx
                result.append((idx, inst, block.label))
                idx += 1
        return result, label_map


@dataclass
class Program:
    function: Function

    def __str__(self) -> str:
        from .printer import print_program

        return print_program(self)
