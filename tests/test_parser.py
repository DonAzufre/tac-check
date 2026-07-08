from __future__ import annotations

import pytest

from src.tac.parser import ParseError, parse_program


def test_parse_straightline():
    src = """
func main(i64 a, i64 b) -> i64
  t0 = const 1
  t1 = add a, b
  ret t1
end
"""
    prog = parse_program(src)
    assert prog.function.name == "main"
    assert prog.function.param_names() == ["a", "b"]
    assert len(prog.function.blocks["entry"].instructions) == 3


def test_parse_cfg():
    src = """
func main(i64 a, i64 b) -> i64
entry:
  c0 = eq a, b
  br c0, then, else

then:
  t0 = const 1
  ret t0

else:
  t0 = const 0
  ret t0
end
"""
    prog = parse_program(src)
    assert "entry" in prog.function.blocks
    assert "then" in prog.function.blocks
    assert "else" in prog.function.blocks


def test_constant_reduction_warning():
    src = """
func main(i64 a) -> i64
  t0 = const 10
  ret t0
end
"""
    with pytest.warns():
        parse_program(src, value_max=7)


def test_parse_rejects_unknown_label():
    src = """
func main(i64 a) -> i64
  jmp missing
end
"""
    with pytest.raises(ParseError, match="undefined label"):
        parse_program(src)


def test_parse_rejects_instruction_after_terminator():
    src = """
func main(i64 a) -> i64
  ret a
  t0 = const 1
end
"""
    with pytest.raises(ParseError, match="after terminator"):
        parse_program(src)


def test_parse_rejects_use_before_definition():
    src = """
func main(i64 a) -> i64
  t0 = add missing, a
  ret t0
end
"""
    with pytest.raises(ParseError, match="before definition"):
        parse_program(src)


def test_parse_rejects_duplicate_label():
    src = """
func main(i64 a) -> i64
L:
  t0 = const 1
L:
  ret t0
end
"""
    with pytest.raises(ParseError, match="duplicate label"):
        parse_program(src)
