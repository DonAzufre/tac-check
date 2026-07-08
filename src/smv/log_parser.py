from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path


_SPEC_RE = re.compile(
    r"--\s+specification\s+(?P<spec>.*?)\s+is\s+(?P<status>true|false)",
    re.IGNORECASE,
)
_STATE_RE = re.compile(r"->\s*State:\s*(?P<state>[^<]+)<-")
_ASSIGN_RE = re.compile(r"\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.+?)\s*$")
_NAME_RE = re.compile(r"\b(BothEventuallyStop|SameNormalOutput|SameTrapBehavior1|SameTrapBehavior2|NoMismatchAtStop|NoTimeout)\b")


@dataclass(frozen=True)
class PropertyResult:
    name: str
    raw_spec: str
    holds: bool


@dataclass
class TraceState:
    name: str
    assignments: dict[str, str] = field(default_factory=dict)


@dataclass
class NuSMVLogSummary:
    properties: list[PropertyResult] = field(default_factory=list)
    trace: list[TraceState] = field(default_factory=list)

    @property
    def failed_properties(self) -> list[PropertyResult]:
        return [prop for prop in self.properties if not prop.holds]

    @property
    def all_properties_hold(self) -> bool:
        return bool(self.properties) and not self.failed_properties


def _property_name(raw_spec: str) -> str:
    match = _NAME_RE.search(raw_spec)
    if match:
        return match.group(1)
    compact = " ".join(raw_spec.split())
    return compact[:80] if compact else "<unknown>"


def parse_nusmv_log(text: str) -> NuSMVLogSummary:
    summary = NuSMVLogSummary()
    current_state: TraceState | None = None

    for line in text.splitlines():
        spec_match = _SPEC_RE.search(line)
        if spec_match:
            raw_spec = spec_match.group("spec").strip()
            status = spec_match.group("status").lower() == "true"
            summary.properties.append(
                PropertyResult(name=_property_name(raw_spec), raw_spec=raw_spec, holds=status)
            )
            continue

        state_match = _STATE_RE.search(line)
        if state_match:
            current_state = TraceState(name=state_match.group("state").strip())
            summary.trace.append(current_state)
            continue

        assign_match = _ASSIGN_RE.match(line)
        if current_state is not None and assign_match:
            current_state.assignments[assign_match.group("name")] = assign_match.group("value")

    return summary


def parse_nusmv_log_file(path: str | Path) -> NuSMVLogSummary:
    return parse_nusmv_log(Path(path).read_text())


def render_markdown_summary(summary: NuSMVLogSummary, title: str = "NuSMV verification summary") -> str:
    lines: list[str] = [f"# {title}", ""]
    if summary.properties:
        lines.append("## Properties")
        lines.append("")
        lines.append("| Property | Result |")
        lines.append("|---|---|")
        for prop in summary.properties:
            lines.append(f"| `{prop.name}` | {'PASS' if prop.holds else 'FAIL'} |")
        lines.append("")
    else:
        lines.append("No NuSMV property result lines were found.")
        lines.append("")

    if summary.failed_properties:
        lines.append("## Failed properties")
        lines.append("")
        for prop in summary.failed_properties:
            lines.append(f"- `{prop.name}`: `{prop.raw_spec}`")
        lines.append("")

    if summary.trace:
        lines.append("## Counterexample / trace excerpt")
        lines.append("")
        interesting_names = {
            "src_pc",
            "opt_pc",
            "src_done",
            "opt_done",
            "src_trap",
            "opt_trap",
            "src_out",
            "opt_out",
            "src_timeout",
            "opt_timeout",
        }
        for state in summary.trace[:12]:
            lines.append(f"### State {state.name}")
            lines.append("")
            shown = {
                k: v
                for k, v in state.assignments.items()
                if k in interesting_names or not k.startswith(("src_", "opt_"))
            }
            if not shown:
                shown = state.assignments
            for name, value in sorted(shown.items()):
                lines.append(f"- `{name}` = `{value}`")
            lines.append("")
    else:
        lines.append("No counterexample trace was found in the log.")
        lines.append("")

    return "\n".join(lines)


def write_markdown_summary(log_path: str | Path, output_path: str | Path, title: str | None = None) -> None:
    log_path = Path(log_path)
    output_path = Path(output_path)
    summary = parse_nusmv_log_file(log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown_summary(summary, title or f"NuSMV verification summary for {log_path.name}")
    )
