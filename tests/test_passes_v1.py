from __future__ import annotations

import pytest

from src.tac.interpreter import run
from src.tac.ir import ConstInst
from src.tac.parser import parse_program
from src.tac.printer import print_program


SRC_CF = """
func main(i64 a) -> i64
  t0 = const 1
  t1 = const 2
  t2 = add t0, t1
  t3 = add a, t2
  ret t3
end
"""

SRC_DCE = """
func main(i64 a) -> i64
  t0 = const 1
  t1 = const 2
  t2 = add t0, t1
  dead = mul t2, t2
  ret t2
end
"""

SRC_CSE = """
func main(i64 a, i64 b) -> i64
  t0 = add a, b
  t1 = add a, b
  t2 = add t0, t1
  ret t2
end
"""


def test_parse_and_print_roundtrip():
    prog = parse_program(SRC_CF)
    text = print_program(prog)
    assert "func main" in text
    assert "ret t3" in text


def test_interpreter_straightline():
    prog = parse_program(SRC_CF)
    result = run(prog, {"a": 5})
    assert result.done
    assert not result.trap
    assert result.out == (5 + 1 + 2) % 8


def test_interpreter_div_by_zero():
    src = """
func main(i64 a) -> i64
  t0 = div a, a
  ret t0
end
"""
    prog = parse_program(src)
    result = run(prog, {"a": 0})
    assert result.trap
    assert not result.done


def test_const_fold():
    from src.passes.const_fold import const_fold_function

    prog = parse_program(SRC_CF)
    folded = const_fold_function(prog.function, value_max=7)
    t2 = folded.blocks["entry"].instructions[2]
    assert isinstance(t2, ConstInst)
    assert t2.value == 3


def test_const_prop():
    from src.passes.const_prop import const_prop_function

    src = """
func main(i64 a) -> i64
  t0 = const 1
  t1 = add t0, a
  ret t1
end
"""
    prog = parse_program(src)
    prop = const_prop_function(prog.function, value_max=7)
    t1 = prop.blocks["entry"].instructions[1]
    assert "1" in str(t1)


def test_dce_removes_unused_pure_computation():
    from src.passes.dce import dce_function

    prog = parse_program(SRC_DCE)
    opt = dce_function(prog.function, value_max=7)
    names = [str(inst) for inst in opt.blocks["entry"].instructions]
    assert "dead = mul" not in names
    assert any("ret t2" in n for n in names)


def test_dce_preserves_div():
    from src.passes.dce import dce_function

    src = """
func main(i64 a) -> i64
  t0 = div a, a
  dead = const 3
  ret dead
end
"""
    prog = parse_program(src)
    opt = dce_function(prog.function, value_max=7)
    names = [str(inst) for inst in opt.blocks["entry"].instructions]
    assert any("div" in n for n in names)


def test_local_cse():
    from src.passes.local_cse import local_cse_function

    prog = parse_program(SRC_CSE)
    opt = local_cse_function(prog.function, value_max=7)
    names = [str(inst) for inst in opt.blocks["entry"].instructions]
    assert any("copy t0" in n for n in names)
