from __future__ import annotations

from src.tac.interpreter import run
from src.tac.parser import parse_program


def test_run_straightline():
    src = """
func main(i64 a) -> i64
  t0 = const 1
  t1 = add a, t0
  ret t1
end
"""
    prog = parse_program(src)
    result = run(prog, {"a": 3})
    assert result.done
    assert result.out == 4


def test_run_div_zero():
    src = """
func main(i64 a) -> i64
  t0 = div a, a
  ret t0
end
"""
    prog = parse_program(src)
    result = run(prog, {"a": 0})
    assert result.trap


def test_run_cfg():
    src = """
func main(i64 a) -> i64
entry:
  c0 = eq a, 0
  br c0, then, else

then:
  t0 = const 1
  ret t0

else:
  t0 = const 2
  ret t0
end
"""
    prog = parse_program(src)
    assert run(prog, {"a": 0}).out == 1
    assert run(prog, {"a": 1}).out == 2
