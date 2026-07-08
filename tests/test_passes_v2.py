from __future__ import annotations

from src.passes.const_fold import const_fold_function
from src.passes.simplify_cfg import (
    branch_fold_function,
    cfg_const_prop_function,
    sccp_function,
    unreachable_elim_function,
)
from src.tac.interpreter import run
from src.tac.ir import Program
from src.tac.parser import parse_program

from .helpers import assert_equiv_on_finite_domain


SRC_BRANCH = """
func main(i64 a) -> i64
entry:
  t0 = const 1
  br t0, then, else

then:
  t1 = const 3
  ret t1

else:
  t2 = const 4
  ret t2
end
"""

SRC_UNREACHABLE = """
func main(i64 a) -> i64
entry:
  t0 = const 1
  ret t0

dead:
  t1 = const 7
  ret t1
end
"""


def test_branch_fold():
    prog = parse_program(SRC_BRANCH)
    folded = const_fold_function(prog.function)
    opt = branch_fold_function(folded)
    entry = opt.blocks["entry"]
    assert any(str(inst).startswith("jmp then") for inst in entry.instructions)
    for a in range(8):
        assert run(prog, {"a": a}).out == run(Program(function=opt), {"a": a}).out


def test_unreachable_elim():
    prog = parse_program(SRC_UNREACHABLE)
    opt = unreachable_elim_function(prog.function)
    assert "dead" not in opt.blocks
    for a in range(8):
        assert run(prog, {"a": a}).out == run(Program(function=opt), {"a": a}).out


def test_cfg_const_prop_across_blocks():
    src = """
func main(i64 a) -> i64
entry:
  x = const 2
  br a, left, right

left:
  y = add x, 1
  ret y

right:
  y = add x, 2
  ret y
end
"""
    prog = parse_program(src)
    opt = cfg_const_prop_function(prog.function)
    text = "\n".join(str(i) for b in opt.blocks.values() for i in b.instructions)
    assert "y = const 3" in text
    assert "y = const 4" in text
    assert_equiv_on_finite_domain(src, cfg_const_prop_function, value_max=3)


def test_sccp():
    src = """
func main(i64 a) -> i64
entry:
  t0 = const 1
  t1 = const 2
  c0 = eq t0, t1
  br c0, then, else

then:
  t2 = const 5
  ret t2

else:
  t2 = const 6
  ret t2
end
"""
    prog = parse_program(src)
    folded = const_fold_function(prog.function)
    opt = sccp_function(folded)
    assert run(prog, {"a": 0}).out == run(Program(function=opt), {"a": 0}).out


def test_finite_domain_equiv_v2_passes():
    for pass_fn in (branch_fold_function, unreachable_elim_function, cfg_const_prop_function, sccp_function):
        assert_equiv_on_finite_domain(SRC_BRANCH, pass_fn, value_max=3)
