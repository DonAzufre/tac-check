# Toy TAC Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based translation-validation tool that compiles simplified TAC programs to NuSMV product machines, verifying semantic equivalence between source and optimized programs under a finite value domain.

**Architecture:** Python frontend parses/optimizes TAC, generates a monolithic `MODULE main` in NuSMV that interleaves source and optimized execution in strict synchronous steps, and exposes a CLI to run the full pipeline. Files are organized by responsibility under `src/tac`, `src/passes`, `src/smv`, and `src/cli`.

**Tech Stack:** Python 3.10+, no heavy dependencies; pytest for tests; NuSMV optional for external verification.

## Global Constraints

- Python 3.10+.
- No complex third-party libraries.
- Generate `.smv` files from Python; never read TAC text dynamically inside SMV.
- All models are finite-state.
- TAC type is `i64`; NuSMV uses finite domain `0..VALUE_MAX` with modular arithmetic.
- Default `VALUE_MAX = 7`; constants are reduced modulo `VALUE_MAX + 1` at parse time with a warning.
- Division by zero produces trap.
- Observable behavior: normal termination, trap, output value `out`.
- Synchronous small-step execution in SMV; done/trap stalls.
- v2 CFG is assumed loop-free; `max_steps` is a safety bound only.
- SMV uses single monolithic `MODULE main`.

---

### Task 1: Project Skeleton

**Files:**
- Create: `README.md`
- Create: `Makefile`
- Create: `requirements.txt`
- Create: `src/tac/__init__.py`
- Create: `src/passes/__init__.py`
- Create: `src/smv/__init__.py`
- Create: `src/cli/__init__.py`
- Create: `tests/__init__.py`
- Create: `generated/tac/.gitkeep`
- Create: `generated/smv/.gitkeep`
- Create: `generated/logs/.gitkeep`
- Create: `generated/counterexamples/.gitkeep`

**Interfaces:**
- Produces: directory layout and build entry points.

- [ ] **Step 1: Create directory tree**
- [ ] **Step 2: Write initial README with project overview, install, run instructions**
- [ ] **Step 3: Write Makefile with `test`, `run-v1`, `run-v2`, `verify-v1`, `verify-bad` targets**
- [ ] **Step 4: Write `requirements.txt` (pytest only)**
- [ ] **Step 5: Create `__init__.py` files**

---

### Task 2: TAC IR

**Files:**
- Create: `src/tac/ir.py`
- Test: `tests/test_ir.py`

**Interfaces:**
- Produces: `Program`, `Function`, `BasicBlock`, `Instruction`, `Operand` dataclasses with helper constructors and visitor support.

- [ ] **Step 1: Define `Operand` union of `Const(int)`, `Var(str)`, `Param(str)`**
- [ ] **Step 2: Define instruction kinds: `Const`, `Copy`, `BinOp`, `Neg`, `Cmp`, `Ret`, `Jmp`, `Br`, `Label`**
- [ ] **Step 3: Define `BasicBlock` with list of instructions, label, successors, predecessors**
- [ ] **Step 4: Define `Function` with name, params, return type, entry block, blocks dict**
- [ ] **Step 5: Define `Program` as container of one function**
- [ ] **Step 6: Write unit tests for construction and helpers**

---

### Task 3: Parser and Printer

**Files:**
- Create: `src/tac/parser.py`
- Create: `src/tac/printer.py`
- Test: `tests/test_parser.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`
- Produces: `parse_program(text: str, value_max: int = 7) -> Program`, `print_program(program: Program) -> str`

- [ ] **Step 1: Implement line-based tokenizer/lexer**
- [ ] **Step 2: Parse function header `func main(i64 a) -> i64`**
- [ ] **Step 3: Parse straight-line instructions: const, copy, add/sub/mul/div/mod, neg, eq/lt, ret**
- [ ] **Step 4: Reduce constants modulo `value_max + 1` and emit warning**
- [ ] **Step 5: Parse CFG instructions: labels, jmp, br**
- [ ] **Step 6: Build basic blocks and successor/predecessor edges**
- [ ] **Step 7: Implement printer outputting canonical TAC text**
- [ ] **Step 8: Write parser tests for v1 and v2 TAC**

---

### Task 4: Interpreter

**Files:**
- Create: `src/tac/interpreter.py`
- Test: `tests/test_interpreter.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`
- Produces: `run(program: Program, inputs: dict[str,int], value_max: int = 7) -> Result` where `Result` has `done`, `trap`, `out`, `steps`.

- [ ] **Step 1: Define `InterpretResult` dataclass**
- [ ] **Step 2: Implement operand resolution against env and params**
- [ ] **Step 3: Implement arithmetic with modulo semantics and div-by-zero trap**
- [ ] **Step 4: Implement straight-line execution**
- [ ] **Step 5: Implement CFG execution with pc over flat instruction list**
- [ ] **Step 6: Add `max_steps` bound returning timeout if exceeded**
- [ ] **Step 7: Write interpreter tests including div-by-zero and timeout**

---

### Task 5: v1 Optimization Passes

**Files:**
- Create: `src/passes/const_fold.py`
- Create: `src/passes/const_prop.py`
- Create: `src/passes/dce.py`
- Create: `src/passes/local_cse.py`
- Test: `tests/test_passes_v1.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`
- Produces: `pass_func(function: Function, value_max: int) -> Function` for each pass.

- [ ] **Step 1: Implement constant folding for arithmetic and comparison operators**
- [ ] **Step 2: Preserve div-by-zero trap by not folding `div c, 0`**
- [ ] **Step 3: Implement local constant propagation within a basic block**
- [ ] **Step 4: Implement DCE preserving ret/br/jmp and potentially-trapping div**
- [ ] **Step 5: Implement local CSE for pure commutative/non-commutative expressions**
- [ ] **Step 6: Compose passes in CLI order**
- [ ] **Step 7: Write v1 pass tests covering correct and incorrect expectations**

---

### Task 6: SMV Generator v1

**Files:**
- Create: `src/smv/smvgen.py`
- Create: `src/smv/properties.py`
- Test: `tests/test_smvgen.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`
- Produces: `generate_smv(source: Program, optimized: Program, value_max: int, max_steps: int) -> str`

- [ ] **Step 1: Flatten straight-line instructions into indexed pc list**
- [ ] **Step 2: Generate nondeterministic input variables**
- [ ] **Step 3: Generate source and optimized pc, step, done, trap, out variables**
- [ ] **Step 4: Generate source and optimized temporary variable declarations**
- [ ] **Step 5: Generate init/next assignments for strict synchronous step semantics**
- [ ] **Step 6: Generate instruction semantics in next-expression form**
- [ ] **Step 7: Generate CTL properties from `src/smv/properties.py`**
- [ ] **Step 8: Write SMV generator tests checking output contains required fragments**

---

### Task 7: CLI

**Files:**
- Create: `src/cli/run.py`

**Interfaces:**
- Consumes: parser, passes, printer, smvgen
- Produces: command-line entry point `python -m src.cli.run <tac> --passes ... --emit-opt ... --emit-smv ... --run-nusmv`

- [ ] **Step 1: Use `argparse` with all required options**
- [ ] **Step 2: Parse input TAC**
- [ ] **Step 3: Apply requested passes in order**
- [ ] **Step 4: Emit optimized TAC file**
- [ ] **Step 5: Generate and emit SMV file**
- [ ] **Step 6: Optionally run NuSMV, capture output, save log**
- [ ] **Step 7: Implement `--bad-pass` handlers (e.g., `div-self-to-one`, `drop-ret-deps`)**
- [ ] **Step 8: Gracefully handle missing NuSMV binary**

---

### Task 8: v1 Examples and Tests

**Files:**
- Create: `examples/v1_straightline/cf_01.tac`
- Create: `examples/v1_straightline/cp_01.tac`
- Create: `examples/v1_straightline/dce_01.tac`
- Create: `examples/v1_straightline/cse_01.tac`
- Create: `examples/v1_straightline/bad_dce_01.tac`
- Create: `examples/v1_straightline/bad_div_01.tac`

- [ ] **Step 1: Write each v1 example file**
- [ ] **Step 2: Verify CLI can parse, optimize, and emit SMV for each**
- [ ] **Step 3: Add integration assertions in pytest where possible**

---

### Task 9: CFG Support

**Files:**
- Create: `src/tac/cfg.py`
- Test: `tests/test_cfg.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`
- Produces: helpers to build CFG, iterate blocks in order, compute reachable blocks, successors/predecessors.

- [ ] **Step 1: Add `Function.add_block`, `Function.set_entry`, block linking helpers**
- [ ] **Step 2: Provide `reachable_blocks(function)` returning set of block labels**
- [ ] **Step 3: Provide `topological_order(function)` for loop-free CFGs**
- [ ] **Step 4: Flatten CFG to indexed instruction list for interpreter and SMV**
- [ ] **Step 5: Write CFG tests**

---

### Task 10: v2 Optimization Passes

**Files:**
- Create: `src/passes/simplify_cfg.py`
- Create: `src/passes/unreachable_elim.py`
- Create: `src/passes/sccp.py`
- Modify: `src/passes/const_fold.py`, `src/passes/const_prop.py` to support CFG
- Test: `tests/test_passes_v2.py`

**Interfaces:**
- Consumes: `src/tac/ir.py`, `src/tac/cfg.py`
- Produces: CFG-aware pass functions.

- [ ] **Step 1: Implement unreachable block elimination**
- [ ] **Step 2: Implement branch folding for constant conditions**
- [ ] **Step 3: Implement CFG-aware constant propagation across blocks**
- [ ] **Step 4: Implement simplified SCCP (UNDEF/CONST/TOP lattice) without phi**
- [ ] **Step 5: Write v2 pass tests**

---

### Task 11: SMV Generator v2

**Files:**
- Modify: `src/smv/smvgen.py`
- Test: `tests/test_smvgen.py` (extend)

**Interfaces:**
- Produces: SMV for CFG programs using flat instruction pc and label resolution.

- [ ] **Step 1: Flatten CFG instructions into indexed pc list with label map**
- [ ] **Step 2: Generate pc transitions for jmp/br/ret/label**
- [ ] **Step 3: Ensure synchronous step semantics still hold**
- [ ] **Step 4: Add timeout property handling**
- [ ] **Step 5: Extend SMV generator tests for CFG**

---

### Task 12: v2 Examples and Tests

**Files:**
- Create: `examples/v2_cfg/branch_fold_01.tac`
- Create: `examples/v2_cfg/unreachable_01.tac`
- Create: `examples/v2_cfg/cfg_cp_01.tac`
- Create: `examples/v2_cfg/sccp_01.tac`
- Create: `examples/v2_cfg/bad_branch_fold_01.tac`

- [ ] **Step 1: Write each v2 example file**
- [ ] **Step 2: Verify CLI pipeline for each**
- [ ] **Step 3: Add integration assertions**

---

### Task 13: Documentation

**Files:**
- Create: `docs/model_design.md`
- Create: `docs/tac_language.md`
- Create: `docs/verification_properties.md`
- Create: `docs/experiment_record_template.md`
- Create: `docs/report_outline.md`
- Modify: `README.md`

- [ ] **Step 1: Document TAC language syntax and semantics**
- [ ] **Step 2: Document model design and finite-domain abstractions**
- [ ] **Step 3: Document all CTL/LTL properties and their meaning**
- [ ] **Step 4: Provide experiment record template**
- [ ] **Step 5: Provide report outline**
- [ ] **Step 6: Update README with final instructions and limitations**

---

### Task 14: Final Verification

- [ ] **Step 1: Run `pytest -q` and fix failures**
- [ ] **Step 2: Run `make run-v1` and `make run-v2` successfully**
- [ ] **Step 3: Run `make verify-bad` if NuSMV available, inspect counterexample**
- [ ] **Step 4: Lint/type-check with `python -m py_compile` on all source files**
