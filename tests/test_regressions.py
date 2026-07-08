from __future__ import annotations

from src.passes.const_fold import const_fold_function
from src.passes.const_prop import const_prop_function
from src.passes.local_cse import local_cse_function
from src.tac.parser import parse_program

from .helpers import assert_equiv_on_finite_domain


def test_const_fold_kills_redefined_variable():
    src = """
func main(i64 a) -> i64
  x = const 1
  x = add a, x
  y = add x, 1
  ret y
end
"""
    assert_equiv_on_finite_domain(src, const_fold_function, value_max=7)
    opt = const_fold_function(parse_program(src).function)
    text = "\n".join(str(inst) for inst in opt.blocks["entry"].instructions)
    assert "y = add 1, 1" not in text


def test_const_prop_kills_redefined_variable():
    src = """
func main(i64 a) -> i64
  x = const 1
  x = add a, x
  y = add x, 1
  ret y
end
"""
    assert_equiv_on_finite_domain(src, const_prop_function, value_max=7)
    opt = const_prop_function(parse_program(src).function)
    text = "\n".join(str(inst) for inst in opt.blocks["entry"].instructions)
    assert "y = add 1, 1" not in text


def test_local_cse_invalidates_redefined_operands():
    src = """
func main(i64 a, i64 b) -> i64
  t0 = add a, b
  a2 = add a, 1
  t1 = add a2, b
  a2 = add a2, 1
  t2 = add a2, b
  ret t2
end
"""
    assert_equiv_on_finite_domain(src, local_cse_function, value_max=3)
    opt = local_cse_function(parse_program(src, value_max=3).function)
    text = "\n".join(str(inst) for inst in opt.blocks["entry"].instructions)
    assert "t2 = copy t1" not in text
