from __future__ import annotations

from src.smv.log_parser import parse_nusmv_log, render_markdown_summary


def test_parse_nusmv_property_results_and_trace():
    log = """
-- specification SameNormalOutput is false
-- as demonstrated by the following execution sequence
Trace Description: CTL Counterexample
Trace Type: Counterexample
  -> State: 1.1 <-
    a = 0
    src_pc = 0
    opt_pc = 0
  -> State: 1.2 <-
    src_trap = TRUE
    opt_trap = FALSE
-- specification NoTimeout is true
"""
    summary = parse_nusmv_log(log)
    assert [p.name for p in summary.properties] == ["SameNormalOutput", "NoTimeout"]
    assert [p.holds for p in summary.properties] == [False, True]
    assert summary.failed_properties[0].name == "SameNormalOutput"
    assert summary.trace[0].assignments["a"] == "0"
    markdown = render_markdown_summary(summary)
    assert "SameNormalOutput" in markdown
    assert "FAIL" in markdown
