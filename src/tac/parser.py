from __future__ import annotations

from .ir import (
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
    LabelInst,
    NegInst,
    Operand,
    Param,
    Program,
    RetInst,
    Var,
)
from .validator import ValidationError, validate_function


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text: str, value_max: int = 7):
        if value_max < 0:
            raise ParseError("value_max must be non-negative")
        self.lines = text.splitlines()
        self.value_max = value_max
        self.mod = value_max + 1
        self.line_no = 0
        self._params: list[str] = []

    def parse(self) -> Program:
        func = self._parse_function()
        return Program(function=func)

    def _param_names(self) -> list[str]:
        return self._params

    def _error(self, msg: str) -> None:
        raise ParseError(f"Line {self.line_no}: {msg}")

    def _peek(self) -> str | None:
        while self.line_no < len(self.lines):
            line = self.lines[self.line_no].strip()
            if line == "" or line.startswith("#"):
                self.line_no += 1
                continue
            return line
        return None

    def _consume(self) -> str:
        line = self._peek()
        if line is None:
            self._error("unexpected end of file")
        self.line_no += 1
        return line

    def _parse_function(self) -> Function:
        line = self._consume()
        if not line.startswith("func "):
            self._error(f"expected function header, got: {line}")
        rest = line[len("func "):].strip()
        if "(" not in rest or ")" not in rest:
            self._error("expected function header 'func name(args) -> ty'")
        name, _, rest = rest.partition("(")
        name = name.strip()
        if not name:
            self._error("empty function name")
        params_part, sep, ret_part = rest.partition(")")
        if sep != ")" or "->" not in ret_part:
            self._error("expected return type '-> ty'")
        ret_ty = ret_part.split("->", 1)[1].strip()
        if not ret_ty:
            self._error("empty return type")
        params = self._parse_params(params_part)
        self._params = [p[0] for p in params]
        func = Function(name=name, params=params, ret_ty=ret_ty, entry="")
        current_label = "entry"
        func.blocks[current_label] = BasicBlock(label=current_label)
        func.entry = current_label
        while True:
            line = self._peek()
            if line is None:
                self._error("expected 'end' before end of file")
            if line == "end":
                self._consume()
                break
            current_label = self._parse_line(func, current_label)
        self._link_blocks(func)
        try:
            validate_function(func)
        except ValidationError as exc:
            self._error(str(exc))
        return func

    def _parse_params(self, text: str) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = []
        if not text.strip():
            return params
        seen: set[str] = set()
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            pieces = part.split()
            if len(pieces) != 2:
                self._error(f"invalid parameter declaration: {part}")
            ty, name = pieces
            if name in seen:
                self._error(f"duplicate parameter: {name}")
            seen.add(name)
            params.append((name, ty))
        return params

    def _parse_line(self, func: Function, current_label: str) -> str:
        line = self._consume()
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label:
                self._error("empty label")
            if label in func.blocks:
                block = func.blocks[label]
                if label == "entry" and not block.instructions:
                    block.instructions.append(LabelInst(name=label))
                    return label
                self._error(f"duplicate label: {label}")
            func.blocks[label] = BasicBlock(label=label)
            func.blocks[label].instructions.append(LabelInst(name=label))
            return label

        block = func.blocks[current_label]
        if block.terminator() is not None:
            self._error(f"instruction appears after terminator in block '{current_label}'")
        inst = self._parse_instruction(line)
        block.instructions.append(inst)
        return current_label

    def _parse_instruction(self, line: str) -> Instruction:
        if line.startswith("ret "):
            return RetInst(src=self._parse_operand(line[4:].strip()))
        if line.startswith("jmp "):
            label = line[4:].strip()
            if not label:
                self._error("empty jump target")
            return JmpInst(label=label)
        if line.startswith("br "):
            parts = [p.strip() for p in line[3:].split(",")]
            if len(parts) != 3:
                self._error(f"invalid branch: {line}")
            cond = self._parse_operand(parts[0])
            if not parts[1] or not parts[2]:
                self._error(f"invalid branch target: {line}")
            return BrInst(cond=cond, true_label=parts[1], false_label=parts[2])

        if "=" not in line:
            self._error(f"unrecognized instruction: {line}")
        lhs, rhs = line.split("=", 1)
        dst = lhs.strip()
        if not dst:
            self._error(f"empty destination: {line}")
        rhs = rhs.strip()
        parts = rhs.split()
        if not parts:
            self._error(f"empty instruction rhs: {line}")
        op = parts[0]
        if op == "const":
            if len(parts) != 2:
                self._error(f"invalid const instruction: {line}")
            raw = int(parts[1])
            reduced = raw % self.mod
            if raw != reduced:
                import warnings

                warnings.warn(
                    f"Line {self.line_no}: constant {raw} reduced to {reduced} (mod {self.mod})"
                )
            return ConstInst(dst=dst, value=reduced)
        if op == "copy":
            if len(parts) != 2:
                self._error(f"invalid copy instruction: {line}")
            return CopyInst(dst=dst, src=self._parse_operand(parts[1]))
        if op == "neg":
            if len(parts) != 2:
                self._error(f"invalid neg instruction: {line}")
            return NegInst(dst=dst, src=self._parse_operand(parts[1]))
        if op in ("add", "sub", "mul", "div", "mod"):
            if len(parts) != 3:
                self._error(f"invalid binary instruction: {line}")
            left = self._parse_operand(parts[1].rstrip(","))
            right = self._parse_operand(parts[2])
            return BinOpInst(dst=dst, op=op, left=left, right=right)
        if op in ("eq", "lt"):
            if len(parts) != 3:
                self._error(f"invalid compare instruction: {line}")
            left = self._parse_operand(parts[1].rstrip(","))
            right = self._parse_operand(parts[2])
            return CmpInst(dst=dst, op=op, left=left, right=right)
        self._error(f"unknown operation: {op}")

    def _parse_operand(self, text: str) -> Operand:
        text = text.strip()
        if not text:
            self._error("empty operand")
        if text.startswith("%") or text.startswith("@"):
            text = text[1:]
        try:
            return Const(value=int(text))
        except ValueError:
            pass
        if text in ("true", "false"):
            return Const(value=1 if text == "true" else 0)
        if text[0].isalpha() or text[0] == "_":
            if text in self._param_names():
                return Param(name=text)
            return Var(name=text)
        self._error(f"invalid operand: {text}")

    def _link_blocks(self, func: Function) -> None:
        labels = list(func.blocks.keys())
        for block in func.blocks.values():
            block.successors = []
            block.predecessors = []

        for label in labels:
            block = func.blocks[label]
            term = block.terminator()
            successors: list[str] = []
            if term is None:
                idx = labels.index(label)
                if idx + 1 < len(labels):
                    successors.append(labels[idx + 1])
            elif isinstance(term, JmpInst):
                successors.append(term.label)
            elif isinstance(term, BrInst):
                successors.extend([term.true_label, term.false_label])
            block.successors = successors

        for label, block in func.blocks.items():
            for succ in block.successors:
                if succ not in func.blocks:
                    self._error(f"block '{label}' jumps to undefined label '{succ}'")
                func.blocks[succ].predecessors.append(label)


def parse_program(text: str, value_max: int = 7) -> Program:
    return Parser(text, value_max).parse()
