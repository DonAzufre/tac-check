# Verification Properties

All properties are generated automatically in the SMV model.

## CTL properties

| Name | Formula | Meaning |
|---|---|---|
| `BothEventuallyStop` | `AF ((src_done \| src_trap) & (opt_done \| opt_trap))` | Both programs eventually reach a final state (normal or trap). |
| `SameNormalOutput` | `AG ((src_done & opt_done) -> src_out = opt_out)` | If both terminate normally, their outputs are equal. |
| `SameTrapBehavior1` | `AG (src_trap -> AF opt_trap)` | If the source traps, the optimized program eventually traps. |
| `SameTrapBehavior2` | `AG (opt_trap -> AF src_trap)` | If the optimized program traps, the source eventually traps. |
| `NoMismatchAtStop` | `AG (((src_done\|src_trap) & (opt_done\|opt_trap)) -> ((src_done & opt_done & src_out=opt_out) \| (src_trap & opt_trap)))` | At any point where both have stopped, either both stopped normally with equal output or both trapped. |
| `NoTimeout` | `AG !(src_timeout \| opt_timeout)` | Neither program times out. |

## Interpreting results

- All properties true: source and optimized behave identically within the modeled bounds.
- `SameNormalOutput` or `NoMismatchAtStop` false: the optimization changed the observable result. NuSMV prints a counterexample trace showing an input value and the diverging final states.
- `SameTrapBehavior*` false: one side traps and the other does not, usually from incorrectly removing or altering a division.
- `NoTimeout` false: a program did not terminate within `max_steps`, likely a loop or missing terminator.

## Counterexample analysis

When NuSMV reports a false property, read the trace:

1. Find the nondeterministic input values (e.g., `a = 0`).
2. Follow `src_pc`/`opt_pc` to see the executed path.
3. Compare `src_out`/`opt_out` and `src_trap`/`opt_trap`.
4. Map the failure back to the optimized TAC and the pass that produced it.
