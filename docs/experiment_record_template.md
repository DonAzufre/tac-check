# Experiment Record Template

## Experiment number

## Source program

Paste the source `.tac` here.

## Optimization passes

List the passes applied and their order.

## Optimized program

Paste the generated `.opt.tac` here.

## Generated model scale

- Source instruction count:
- Optimized instruction count:
- Value domain:
- Input variable count:
- Temporary variable count:
- Max steps:

## Verification properties

| Property | Expected | Actual | Notes |
|---|---|---|---|
| BothEventuallyStop | true | | |
| SameNormalOutput | true | | |
| SameTrapBehavior1 | true | | |
| SameTrapBehavior2 | true | | |
| NoMismatchAtStop | true | | |
| NoTimeout | true | | |

## NuSMV output summary

Paste the relevant lines from the log.

## Counterexample analysis

If any property is false, explain the input values and the observed mismatch.

## Conclusion

State whether the optimization is verified within the finite model bounds.
