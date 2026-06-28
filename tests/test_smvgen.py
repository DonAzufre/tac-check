from __future__ import annotations

from src.passes.const_fold import const_fold_function
from src.passes.const_prop import const_prop_function
from src.passes.dce import dce_function
from src.smv.smvgen import generate_smv_program
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


from src.tac.ir import Program
