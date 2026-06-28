# Report Outline

## 1. Tool Understanding

Brief introduction to NuSMV and model checking. Explain why CTL is used for this project.

## 2. Case Background

Motivation: verifying compiler optimization correctness. Why translation validation instead of proving passes directly.

## 3. TAC IR Design

Describe the TAC syntax, instruction set, and the distinction between v1 straight-line and v2 CFG.

## 4. Optimization Pass Design

For each implemented pass, explain its purpose and give an example transformation:

- constant folding
- constant propagation
- dead code elimination
- local common subexpression elimination
- branch folding
- unreachable block elimination
- CFG-aware constant propagation
- simplified SCCP

## 5. NuSMV Modeling Method

Explain the product machine, synchronous execution, finite value domain, pc modeling, and trap/timeout handling.

## 6. Verification Properties

List the CTL properties and explain what each one checks.

## 7. Experimental Results

Present the results for each example. Include source/optimized TAC, model scale, and property outcomes.

## 8. Counterexample Analysis

Discuss the deliberately incorrect optimizations (`bad_div_01`, `bad_branch_fold_01`). Show how NuSMV traces expose the bug.

## 9. State Explosion and Modeling Boundaries

Discuss the finite domain limitation, the effect of `VALUE_MAX` and `max_steps`, and what conclusions can and cannot be drawn.

## 10. Conclusion

Summarize what was learned and suggest future extensions (e.g., loops with unwinding, phi nodes, more aggressive passes).
