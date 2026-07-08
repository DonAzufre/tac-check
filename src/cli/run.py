from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ..passes.bad_passes import div_self_to_one_function, drop_ret_deps_function
from ..passes.const_fold import const_fold_function
from ..passes.const_prop import const_prop_function
from ..passes.dce import dce_function
from ..passes.local_cse import local_cse_function
from ..passes.simplify_cfg import (
    branch_fold_function,
    cfg_const_prop_function,
    sccp_function,
    unreachable_elim_function,
)
from ..smv.log_parser import write_markdown_summary
from ..smv.smvgen import generate_smv_program
from ..tac.ir import Program
from ..tac.parser import ParseError, parse_program
from ..tac.printer import print_program


PASS_MAP = {
    "const-fold": const_fold_function,
    "const-prop": const_prop_function,
    "dce": dce_function,
    "local-cse": local_cse_function,
    "branch-fold": branch_fold_function,
    "unreachable-elim": unreachable_elim_function,
    "cfg-cp": cfg_const_prop_function,
    "sccp": sccp_function,
}

BAD_PASS_MAP = {
    "div-self-to-one": div_self_to_one_function,
    "drop-ret-deps": drop_ret_deps_function,
}


def _ensure_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _run_nusmv(smv_path: str, log_path: str, nusmv_bin: str) -> int:
    try:
        result = subprocess.run(
            [nusmv_bin, smv_path],
            capture_output=True,
            text=True,
            check=False,
        )
        _ensure_dir(log_path)
        with open(log_path, "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)
        print(f"NuSMV output saved to {log_path}")
        if result.returncode != 0:
            print(f"NuSMV exited with code {result.returncode}")
        return result.returncode
    except FileNotFoundError:
        print(
            f"NuSMV binary '{nusmv_bin}' not found. "
            "Install NuSMV or pass --nusmv-bin to run verification.",
            file=sys.stderr,
        )
        return 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Toy TAC verification CLI")
    parser.add_argument("input", help="Input .tac file")
    parser.add_argument("--passes", default="", help="Comma-separated pass names")
    parser.add_argument("--bad-pass", default=None, help="Deliberately broken pass name")
    parser.add_argument("--value-max", type=int, default=7, help="Finite value domain upper bound")
    parser.add_argument("--max-steps", type=int, default=32, help="Max execution steps")
    parser.add_argument("--emit-opt", help="Write optimized TAC to this file")
    parser.add_argument("--emit-smv", help="Write generated SMV to this file")
    parser.add_argument("--run-nusmv", action="store_true", help="Run NuSMV after generation")
    parser.add_argument("--nusmv-bin", default="NuSMV", help="NuSMV executable name/path")
    parser.add_argument("--save-log", help="NuSMV log path")
    parser.add_argument(
        "--save-summary",
        help="Markdown summary path for parsed NuSMV results; defaults to generated/counterexamples/<case>.md when --run-nusmv is used",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        with open(args.input, "r") as f:
            source_text = f.read()
        source = parse_program(source_text, value_max=args.value_max)
    except OSError as exc:
        print(f"Cannot read input: {exc}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1

    optimized = source
    for name in [p.strip() for p in args.passes.split(",") if p.strip()]:
        if name not in PASS_MAP:
            print(f"Unknown pass: {name}", file=sys.stderr)
            return 1
        optimized = Program(
            function=PASS_MAP[name](optimized.function, value_max=args.value_max)
        )

    if args.bad_pass:
        if args.bad_pass not in BAD_PASS_MAP:
            print(f"Unknown bad pass: {args.bad_pass}", file=sys.stderr)
            return 1
        optimized = Program(
            function=BAD_PASS_MAP[args.bad_pass](optimized.function, value_max=args.value_max)
        )

    if args.emit_opt:
        _ensure_dir(args.emit_opt)
        with open(args.emit_opt, "w") as f:
            f.write(print_program(optimized))
        print(f"Optimized TAC written to {args.emit_opt}")

    if args.emit_smv:
        _ensure_dir(args.emit_smv)
        smv_text = generate_smv_program(source, optimized, args.value_max, args.max_steps)
        with open(args.emit_smv, "w") as f:
            f.write(smv_text)
        print(f"SMV model written to {args.emit_smv}")

    if args.run_nusmv:
        if not args.emit_smv:
            print("--run-nusmv requires --emit-smv", file=sys.stderr)
            return 1
        log_path = args.save_log or (
            f"generated/logs/{Path(args.input).stem}.log"
        )
        returncode = _run_nusmv(args.emit_smv, log_path, args.nusmv_bin)
        if returncode == 0:
            summary_path = args.save_summary or (
                f"generated/counterexamples/{Path(args.input).stem}.md"
            )
            write_markdown_summary(log_path, summary_path)
            print(f"NuSMV markdown summary written to {summary_path}")
        return returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
