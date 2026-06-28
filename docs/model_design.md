# Model Design

## Translation validation approach

This project does not prove that an optimization pass is correct for all programs. Instead, for each concrete source program and each concrete optimized program, it generates a NuSMV product machine and asks whether the two programs have the same observable behavior on all inputs within the finite value domain.

The optimization passes run in Python; NuSMV only checks the result.

## Why a finite value domain

Model checking requires a finite state space. Real `i64` semantics would be far too large. We therefore interpret `i64` as the finite set `0..VALUE_MAX` with modular arithmetic. This gives a sound but bounded correctness guarantee: any counterexample found in the model is a real semantic mismatch, but a passing check does not prove correctness for full 64-bit integers.

## Product machine

The generated `MODULE main` contains two copies of the program state:

- Source: `src_pc`, `src_done`, `src_trap`, `src_out`, source temporaries
- Optimized: `opt_pc`, `opt_done`, `opt_trap`, `opt_out`, optimized temporaries

Both share the same nondeterministic input variables, so every execution corresponds to running source and optimized on identical inputs.

## Synchronous execution

Each NuSMV transition advances both programs by one instruction. When one side reaches `ret` or a trap, it stalls at its final pc. The other side continues until it also terminates or traps. This models "same input, compare final behavior" while keeping the transition relation simple.

## Program counter

Instructions are flattened into a single list indexed by `pc`. Labels are resolved to indices before SMV generation. A special pc value `N` (past the last instruction) represents the terminated state.

## Trap and timeout

- `div`/`mod` by zero sets the corresponding `trap` flag.
- A `timeout` flag is set if a program exceeds `max_steps` without terminating.
- Both trap and timeout are treated as observable abnormal behavior.

## State-space control

The main sources of state explosion are the value domain and the number of variables. The default value domain is `0..7`. Increasing it or adding many temporaries grows the BDD-based state space quickly.
