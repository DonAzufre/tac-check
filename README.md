# Toy TAC Verification

A course-scale translation-validation project: verify that simple TAC optimization passes preserve observable semantics by generating NuSMV product machines.

## What this project does

1. Parses a simplified three-address code (TAC) program.
2. Applies optimization passes in Python.
3. Generates a NuSMV model that runs the source and optimized programs in lock-step on the same nondeterministic inputs.
4. Checks CTL properties that relate the two programs' final behavior: normal termination, trap, and output value.
5. Optionally parses NuSMV logs into a Markdown counterexample/verification summary.

**Important:** The verification conclusion is valid only within the finite abstract value domain used by the NuSMV model (default `0..7` with modular arithmetic). It is not a proof for full 64-bit integer semantics.

## Requirements

- Python 3.10+
- `pytest` (install from `requirements.txt`)
- NuSMV (optional, for actually running model checks; the tool generates `.smv` files regardless)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

Generate optimized TAC and SMV for a straight-line example:

```bash
make run-v1
```

Generate and run NuSMV:

```bash
make verify-v1
```

Run tests:

```bash
make test
```

Run syntax-level linting:

```bash
make lint
```

## CLI

```bash
python -m src.cli.run examples/v1_straightline/cf_01.tac \
  --passes const-fold,const-prop,dce \
  --value-max 7 --max-steps 32 \
  --emit-opt generated/tac/cf_01.opt.tac \
  --emit-smv generated/smv/cf_01.smv \
  --run-nusmv
```

Options:

- `--passes`: comma-separated pass names applied in order.
- `--bad-pass`: apply a deliberately broken pass for counterexample experiments.
- `--value-max`: upper bound of the finite value domain (default 7).
- `--max-steps`: step bound to avoid unbounded execution (default 32).
- `--emit-opt`: write optimized TAC to file.
- `--emit-smv`: write generated NuSMV model to file.
- `--run-nusmv`: invoke NuSMV and save the log.
- `--nusmv-bin`: path to the NuSMV executable.
- `--save-log`: log file path (default `generated/logs/<case>.log`).
- `--save-summary`: Markdown summary path for parsed NuSMV results (default `generated/counterexamples/<case>.md` when `--run-nusmv` is used).

## Supported TAC instructions

### v1 straight-line

- `v = const N`
- `v = copy x`
- `v = add x, y`
- `v = sub x, y`
- `v = mul x, y`
- `v = div x, y`
- `v = mod x, y`
- `v = neg x`
- `v = eq x, y`
- `v = lt x, y`
- `ret x`

### v2 CFG

Same instructions plus:

- `label:`
- `jmp label`
- `br cond, label_true, label_false`

The parser validates duplicate labels, undefined branch/jump targets, instructions after terminators, unknown parameters, and variable use before definition.

## Supported passes

### v1

- `const-fold`: block-local constant folding with correct invalidation on redefinition.
- `const-prop`: block-local constant propagation with correct invalidation on redefinition.
- `dce`: dead code elimination that preserves potentially trapping division/modulo operations.
- `local-cse`: local common subexpression elimination with operand/result invalidation after writes.

### v2

- `branch-fold`: fold constant-condition branches.
- `unreachable-elim`: delete unreachable blocks.
- `cfg-cp`: CFG-aware must-constant propagation over predecessor intersections.
- `sccp`: simplified SCCP-style pipeline (`cfg-cp` + branch folding + unreachable elimination).

### Bad passes (for counterexamples)

- `div-self-to-one`: incorrectly replaces `x / x` with `1`, causing a mismatch when `x = 0`.
- `drop-ret-deps`: removes instructions even if they feed into `ret`.

## Testing strategy

Tests include:

- parser/validator checks for malformed TAC;
- interpreter behavior checks;
- pass-specific transformation checks;
- finite-domain differential tests comparing source and optimized interpreter observations;
- SMV generation regression tests for full input-domain initialization and correct variable prefixing;
- NuSMV log parser tests.

## Documentation

See `docs/`:

- `tac_language.md`: TAC syntax and semantics.
- `model_design.md`: how the NuSMV model is built.
- `verification_properties.md`: CTL properties and their meaning.
- `experiment_record_template.md`: template for recording experiments.
- `report_outline.md`: suggested report outline.
- `zh_CN/user_guide.md`: detailed Chinese project guide, architecture notes, verification workflow, and extension guide.

## Modeling boundaries and limitations

- TAC type is `i64`, but NuSMV uses a finite domain `0..VALUE_MAX`.
- All arithmetic is modular over `VALUE_MAX + 1`.
- Division by zero is a trap.
- v2 CFG examples are assumed loop-free; `max-steps` is only a safety bound.
- Phi nodes are not supported in v2.
- Verification is translation validation of a specific source/optimized pair, not a general proof about the passes themselves.

## License

Course project.
