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


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text: str, value_max: int = 7):
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
        name, _, rest = rest.partition("(")
        name = name.strip()
        params_part, _, ret_part = rest.partition(")")
        if "->" not in ret_part:
            self._error("expected return type '-> ty'")
        ret_ty = ret_part.split("->")[1].strip()
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
            self._parse_line(func, current_label)
            if line.endswith(":"):
                current_label = line[:-1]
        self._link_blocks(func)
        return func

    def _parse_params(self, text: str) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = []
        if not text.strip():
            return params
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            ty, name = part.split()
            params.append((name, ty))
        return params

    def _parse_line(self, func: Function, current_label: str) -> None:
        line = self._consume()
        if line.endswith(":"):
            label = line[:-1]
            func.blocks[label] = BasicBlock(label=label)
            func.blocks[label].instructions.append(LabelInst(name=label))
            return
        block = func.blocks[current_label]
        inst = self._parse_instruction(line)
        block.instructions.append(inst)

    def _parse_instruction(self, line: str) -> Instruction:
        if line.startswith("ret "):
            return RetInst(src=self._parse_operand(line[4:].strip()))
        if line.startswith("jmp "):
            return JmpInst(label=line[4:].strip())
        if line.startswith("br "):
            parts = [p.strip() for p in line[3:].split(",")]
            if len(parts) != 3:
                self._error(f"invalid branch: {line}")
            cond = self._parse_operand(parts[0])
            return BrInst(cond=cond, true_label=parts[1], false_label=parts[2])

        if "=" not in line:
            self._error(f"unrecognized instruction: {line}")
        lhs, rhs = line.split("=", 1)
        dst = lhs.strip()
        rhs = rhs.strip()
        parts = rhs.split()
        op = parts[0]
        if op == "const":
            raw = int(parts[1])
            reduced = raw % self.mod
            if raw != reduced:
                import warnings

                warnings.warn(
                    f"Line {self.line_no}: constant {raw} reduced to {reduced} (mod {self.mod})"
                )
            return ConstInst(dst=dst, value=reduced)
        if op == "copy":
            return CopyInst(dst=dst, src=self._parse_operand(parts[1]))
        if op == "neg":
            return NegInst(dst=dst, src=self._parse_operand(parts[1]))
        if op in ("add", "sub", "mul", "div", "mod"):
            left = self._parse_operand(parts[1].rstrip(","))
            right = self._parse_operand(parts[2])
            return BinOpInst(dst=dst, op=op, left=left, right=right)
        if op in ("eq", "lt"):
            left = self._parse_operand(parts[1].rstrip(","))
            right = self._parse_operand(parts[2])
            return CmpInst(dst=dst, op=op, left=left, right=right)
        self._error(f"unknown operation: {op}")

    def _parse_operand(self, text: str) -> Operand:
        text = text.strip()
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
        block_order: list[str] = []
        visited: set[str] = set()

        def dfs(label: str) -> None:
            if label in visited:
                return
            visited.add(label)
            block = func.blocks[label]
            term = block.terminator()
            if term is None:
                next_label = None
                idx = labels.index(label)
                if idx + 1 < len(labels):
                    next_label = labels[idx + 1]
                if next_label is not None:
                    block.successors.append(next_label)
            elif isinstance(term, JmpInst):
                block.successors.append(term.label)
            elif isinstance(term, BrInst):
                block.successors.extend([term.true_label, term.false_label])
            for succ in block.successors:
                if succ in func.blocks:
                    func.blocks[succ].predecessors.append(label)
                dfs(succ)

        dfs(func.entry)


def parse_program(text: str, value_max: int = 7) -> Program:
    return Parser(text, value_max).parse()
