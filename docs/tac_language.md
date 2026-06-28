# TAC Language

## Syntax

A program is a single function:

```text
func name(ty param, ...) -> ty
  instructions...
end
```

### Types

The concrete syntax uses `i64` for all integer values. Verification uses a finite abstract domain `0..VALUE_MAX` with modular arithmetic.

### Instructions

#### v1 straight-line

- `v = const N` — integer constant (reduced modulo `VALUE_MAX+1` at parse time)
- `v = copy x`
- `v = add x, y`
- `v = sub x, y`
- `v = mul x, y`
- `v = div x, y` — traps if `y == 0`
- `v = mod x, y` — traps if `y == 0`
- `v = neg x`
- `v = eq x, y` — returns 1 if equal, else 0
- `v = lt x, y` — returns 1 if less-than, else 0
- `ret x`

#### v2 CFG

Same as v1 plus:

- `label:` — basic block label
- `jmp label` — unconditional jump
- `br cond, true_label, false_label` — conditional branch

### Operands

- Constants: integer literals
- Variables: any identifier that is not a parameter
- Parameters: identifiers declared in the function header

## Example

```text
func main(i64 a, i64 b) -> i64
  t0 = add a, b
  t1 = mul t0, t0
  ret t1
end
```

## Semantics

- All arithmetic is modular over `VALUE_MAX + 1`.
- Division or modulo by zero is a trap.
- A function returns the value of its `ret` operand.
- CFG programs are assumed loop-free; execution follows block successors.

## Limitations

- No phi nodes.
- No function calls.
- No memory or I/O beyond the function return value.
