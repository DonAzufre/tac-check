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
    JmpInst,
    LabelInst,
    NegInst,
    Operand,
    Param,
    RetInst,
    Var,
)


def _smv_id(name: str) -> str:
    if name.startswith("in_"):
        return name
    return name.replace(".", "_")


def _operand_smv(op: Operand, prefix: str | None = None) -> str:
    if isinstance(op, Const):
        return str(op.value)
    if isinstance(op, Param):
        return _smv_id(op.name)
    if isinstance(op, Var):
        base = _smv_id(op.name)
        if prefix is None:
            return base
        return f"{prefix}_{base}"
    raise ValueError(f"unknown operand {op}")


def _value_domain_smv(value_max: int) -> str:
    return "{" + ", ".join(str(i) for i in range(value_max + 1)) + "}"


def _declare_var(name: str, value_max: int) -> str:
    return f"  {_smv_id(name)} : 0..{value_max};"


def _assign_var(name: str, expr: str) -> str:
    return f"    {_smv_id(name)} := {expr};"


def _binop_smv(op: str, left: str, right: str, mod: int) -> str:
    if op == "add":
        return f"({left} + {right}) mod {mod}"
    if op == "sub":
        return f"({left} - {right}) mod {mod}"
    if op == "mul":
        return f"({left} * {right}) mod {mod}"
    if op == "div":
        return f"case {right} = 0 : 0; TRUE : {left} / {right}; esac"
    if op == "mod":
        return f"case {right} = 0 : 0; TRUE : {left} mod {right}; esac"
    raise ValueError(f"unknown binop {op}")


def _cmp_smv(op: str, left: str, right: str) -> str:
    if op == "eq":
        return f"case {left} = {right} : 1; TRUE : 0; esac"
    if op == "lt":
        return f"case {left} < {right} : 1; TRUE : 0; esac"
    raise ValueError(f"unknown cmp {op}")


def _collect_vars(func: Function) -> set[str]:
    vars_: set[str] = set()
    for block in func.blocks.values():
        for inst in block.instructions:
            if hasattr(inst, "dst"):
                vars_.add(inst.dst)
            for attr in ("src", "left", "right", "cond"):
                val = getattr(inst, attr, None)
                if isinstance(val, Var):
                    vars_.add(val.name)
    return vars_


def _flatten_with_labels(func: Function) -> tuple[list[tuple[int, Instruction]], dict[str, int]]:
    flat: list[tuple[int, Instruction]] = []
    label_map: dict[str, int] = {}
    idx = 0
    for block in func.ordered_blocks():
        for inst in block.instructions:
            if isinstance(inst, LabelInst):
                label_map[inst.name] = idx
            flat.append((idx, inst))
            idx += 1
    return flat, label_map


def _inst_expr_smv(prefix: str, inst: Instruction, mod: int) -> str | None:
    if isinstance(inst, ConstInst):
        return str(inst.value)
    if isinstance(inst, CopyInst):
        return _operand_smv(inst.src, prefix)
    if isinstance(inst, BinOpInst):
        left = _operand_smv(inst.left, prefix)
        right = _operand_smv(inst.right, prefix)
        return _binop_smv(inst.op, left, right, mod)
    if isinstance(inst, NegInst):
        src = _operand_smv(inst.src, prefix)
        return f"({mod} - {src}) mod {mod}"
    if isinstance(inst, CmpInst):
        left = _operand_smv(inst.left, prefix)
        right = _operand_smv(inst.right, prefix)
        return _cmp_smv(inst.op, left, right)
    return None


def generate_smv(source: Function, optimized: Function, value_max: int, max_steps: int) -> str:
    if value_max < 0:
        raise ValueError("value_max must be non-negative")
    if max_steps < 0:
        raise ValueError("max_steps must be non-negative")

    mod = value_max + 1
    src_flat, src_labels = _flatten_with_labels(source)
    opt_flat, opt_labels = _flatten_with_labels(optimized)
    src_n = len(src_flat)
    opt_n = len(opt_flat)
    params = source.param_names()

    lines: list[str] = []
    lines.append("MODULE main")
    lines.append("")
    lines.append("VAR")
    for p in params:
        lines.append(f"  {_smv_id(p)} : 0..{value_max};")

    lines.append(f"  src_pc : 0..{src_n};")
    lines.append(f"  opt_pc : 0..{opt_n};")
    lines.append(f"  src_step : 0..{max_steps};")
    lines.append(f"  opt_step : 0..{max_steps};")
    lines.append("  src_done : boolean;")
    lines.append("  opt_done : boolean;")
    lines.append("  src_trap : boolean;")
    lines.append("  opt_trap : boolean;")
    lines.append(f"  src_out : 0..{value_max};")
    lines.append(f"  opt_out : 0..{value_max};")
    lines.append("  src_timeout : boolean;")
    lines.append("  opt_timeout : boolean;")

    src_vars = sorted(_collect_vars(source))
    opt_vars = sorted(_collect_vars(optimized))
    for v in src_vars:
        lines.append(_declare_var(f"src_{v}", value_max))
    for v in opt_vars:
        lines.append(_declare_var(f"opt_{v}", value_max))

    lines.append("")
    lines.append("ASSIGN")

    # init
    lines.append("  init(src_pc) := 0;")
    lines.append("  init(opt_pc) := 0;")
    lines.append("  init(src_step) := 0;")
    lines.append("  init(opt_step) := 0;")
    lines.append("  init(src_done) := FALSE;")
    lines.append("  init(opt_done) := FALSE;")
    lines.append("  init(src_trap) := FALSE;")
    lines.append("  init(opt_trap) := FALSE;")
    lines.append("  init(src_out) := 0;")
    lines.append("  init(opt_out) := 0;")
    lines.append("  init(src_timeout) := FALSE;")
    lines.append("  init(opt_timeout) := FALSE;")
    domain = _value_domain_smv(value_max)
    for p in params:
        lines.append(f"  init({_smv_id(p)}) := {domain};")
    for v in src_vars:
        lines.append(f"  init(src_{_smv_id(v)}) := 0;")
    for v in opt_vars:
        lines.append(f"  init(opt_{_smv_id(v)}) := 0;")

    # next for inputs
    for p in params:
        lines.append(f"  next({_smv_id(p)}) := {_smv_id(p)};")

    # helper to generate next pc/out/done/trap for a program
    def _gen_program(
        prefix: str,
        flat: list[tuple[int, Instruction]],
        labels: dict[str, int],
    ) -> list[str]:
        n = len(flat)
        out: list[str] = []
        out.append(f"  next({prefix}_pc) :=")
        out.append("    case")
        out.append(f"      {prefix}_done | {prefix}_trap | {prefix}_timeout : {prefix}_pc;")
        for idx, inst in flat:
            if isinstance(inst, RetInst):
                out.append(f"      {prefix}_pc = {idx} : {n};")
            elif isinstance(inst, JmpInst):
                target = labels.get(inst.label, n)
                out.append(f"      {prefix}_pc = {idx} : {target};")
            elif isinstance(inst, BrInst):
                cond = _operand_smv(inst.cond, prefix)
                target_t = labels.get(inst.true_label, n)
                target_f = labels.get(inst.false_label, n)
                out.append(
                    f"      {prefix}_pc = {idx} : case {cond} != 0 : {target_t}; TRUE : {target_f}; esac;"
                )
            else:
                out.append(f"      {prefix}_pc = {idx} : {idx + 1};")
        out.append(f"      TRUE : {n};")
        out.append("    esac;")

        out.append(f"  next({prefix}_done) :=")
        out.append("    case")
        out.append(f"      {prefix}_done : TRUE;")
        for idx, inst in flat:
            if isinstance(inst, RetInst):
                out.append(f"      {prefix}_pc = {idx} : TRUE;")
        out.append(f"      {prefix}_pc = {n} : TRUE;")
        out.append("      TRUE : FALSE;")
        out.append("    esac;")

        out.append(f"  next({prefix}_trap) :=")
        out.append("    case")
        out.append(f"      {prefix}_trap : TRUE;")
        for idx, inst in flat:
            if isinstance(inst, BinOpInst) and inst.op in ("div", "mod"):
                right = _operand_smv(inst.right, prefix)
                out.append(f"      {prefix}_pc = {idx} & {right} = 0 : TRUE;")
        out.append("      TRUE : FALSE;")
        out.append("    esac;")

        out.append(f"  next({prefix}_out) :=")
        out.append("    case")
        out.append(f"      {prefix}_done : {prefix}_out;")
        for idx, inst in flat:
            if isinstance(inst, RetInst):
                srcv = _operand_smv(inst.src, prefix)
                out.append(f"      {prefix}_pc = {idx} : {srcv};")
        out.append(f"      {prefix}_pc = {n} : {prefix}_out;")
        out.append("      TRUE : 0;")
        out.append("    esac;")

        out.append(f"  next({prefix}_step) :=")
        out.append("    case")
        out.append(f"      {prefix}_done | {prefix}_trap | {prefix}_timeout : {prefix}_step;")
        out.append(f"      {prefix}_pc < {n} & {prefix}_step < {max_steps} : {prefix}_step + 1;")
        out.append(f"      TRUE : {prefix}_step;")
        out.append("    esac;")

        out.append(f"  next({prefix}_timeout) :=")
        out.append("    case")
        out.append(f"      {prefix}_timeout : TRUE;")
        out.append(
            f"      !{prefix}_done & !{prefix}_trap & {prefix}_step >= {max_steps} : TRUE;"
        )
        out.append("      TRUE : FALSE;")
        out.append("    esac;")

        return out

    lines.extend(_gen_program("src", src_flat, src_labels))
    lines.extend(_gen_program("opt", opt_flat, opt_labels))

    # variable updates
    def _gen_var_updates(prefix: str, flat: list[tuple[int, Instruction]], vars_: list[str]) -> list[str]:
        out: list[str] = []
        for v in vars_:
            out.append(f"  next({prefix}_{_smv_id(v)}) :=")
            out.append("    case")
            out.append(f"      {prefix}_done | {prefix}_trap | {prefix}_timeout : {prefix}_{_smv_id(v)};")
            writes = []
            for idx, inst in flat:
                dst = getattr(inst, "dst", None)
                if dst == v:
                    expr = _inst_expr_smv(prefix, inst, mod)
                    if expr is not None:
                        writes.append((idx, expr))
            for idx, expr in writes:
                out.append(f"      {prefix}_pc = {idx} : {expr};")
            out.append(f"      TRUE : {prefix}_{_smv_id(v)};")
            out.append("    esac;")
        return out

    lines.extend(_gen_var_updates("src", src_flat, src_vars))
    lines.extend(_gen_var_updates("opt", opt_flat, opt_vars))

    lines.append("")
    lines.append("CTLSPEC NAME BothEventuallyStop :=")
    lines.append("  AF ((src_done | src_trap) & (opt_done | opt_trap))")
    lines.append("")
    lines.append("CTLSPEC NAME SameNormalOutput :=")
    lines.append("  AG ((src_done & opt_done) -> src_out = opt_out)")
    lines.append("")
    lines.append("CTLSPEC NAME SameTrapBehavior1 :=")
    lines.append("  AG (src_trap -> AF opt_trap)")
    lines.append("")
    lines.append("CTLSPEC NAME SameTrapBehavior2 :=")
    lines.append("  AG (opt_trap -> AF src_trap)")
    lines.append("")
    lines.append("CTLSPEC NAME NoMismatchAtStop :=")
    lines.append("  AG (((src_done | src_trap) & (opt_done | opt_trap)) ->")
    lines.append("      ((src_done & opt_done & src_out = opt_out) |")
    lines.append("       (src_trap & opt_trap)))")
    lines.append("")
    lines.append("CTLSPEC NAME NoTimeout :=")
    lines.append("  AG !(src_timeout | opt_timeout)")

    return "\n".join(lines)


def generate_smv_program(source, optimized, value_max: int, max_steps: int) -> str:
    return generate_smv(source.function, optimized.function, value_max, max_steps)
