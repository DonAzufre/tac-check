from __future__ import annotations

from src.passes.const_fold import const_fold_function
from src.passes.const_prop import const_prop_function
from src.passes.dce import dce_function
from src.smv.smvgen import generate_smv_program
from src.tac.ir import Program
from src.tac.parser import parse_program


def test_smv_generator_contains_key_fragments():
    src = """
func main(i64 a) -> i64
  t0 = const 1
  t1 = add a, t0
  ret t1
end
"""
    prog = parse_program(src)
    opt = const_fold_function(const_prop_function(dce_function(prog.function)))
    smv = generate_smv_program(prog, Program(function=opt), value_max=7, max_steps=16)
    assert "MODULE main" in smv
    assert "CTLSPEC NAME SameNormalOutput" in smv
    assert "src_done" in smv
    assert "opt_done" in smv


def test_smv_inputs_cover_full_finite_domain():
    src = """
func main(i64 a) -> i64
  ret a
end
"""
    prog = parse_program(src, value_max=3)
    smv = generate_smv_program(prog, prog, value_max=3, max_steps=8)
    assert "init(a) := {0, 1, 2, 3};" in smv


def test_smv_var_operands_are_prefixed_for_copy_and_trap():
    src = """
func main(i64 a) -> i64
  x = copy a
  y = div a, x
  z = copy y
  ret z
end
"""
    prog = parse_program(src)
    smv = generate_smv_program(prog, prog, value_max=7, max_steps=16)
    assert "src_pc = 1 & src_x = 0 : TRUE;" in smv
    assert "src_pc = 2 : src_y;" in smv
    assert "opt_pc = 1 & opt_x = 0 : TRUE;" in smv
    assert "opt_pc = 2 : opt_y;" in smv
