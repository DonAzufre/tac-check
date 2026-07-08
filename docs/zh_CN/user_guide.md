# Toy TAC Verification 中文使用与实现文档

本文档面向课程实验、代码审阅和后续扩展开发，系统说明 `tac-check` 的目标、TAC 语言、优化 pass、NuSMV 建模方法、验证性质、测试策略、反例解析流程和已知边界。

## 1. 项目目标

`tac-check` 是一个课程规模的 translation validation 工具。它不试图证明某个优化 pass 对所有程序都正确，而是针对一个具体 TAC 源程序和优化后 TAC 程序生成 NuSMV product machine，检查二者在有限值域内是否具有相同的可观察行为。

核心流程如下：

1. 读取 `.tac` 文本。
2. 解析为 Python dataclass 表示的 TAC IR。
3. 对 IR 应用一个或多个优化 pass。
4. 将源程序和优化后程序同时编码进一个 NuSMV `MODULE main`。
5. 使用共享的非确定输入变量枚举有限输入域。
6. 通过 CTL 性质检查源程序和优化程序是否最终同样正常结束、同样 trap，且正常结束时输出一致。
7. 如果 NuSMV 给出反例，可以把日志解析为 Markdown 摘要，用于报告撰写。

## 2. 有限值域语义

TAC 表面上写作 `i64`，但 NuSMV 模型检查必须是有限状态。因此项目采用有限抽象域：

```text
0..VALUE_MAX
```

默认 `VALUE_MAX = 7`，也就是值域 `0..7`。算术语义如下：

- `add/sub/mul/neg` 使用模 `VALUE_MAX + 1` 的 modular arithmetic；
- `div/mod` 对非零右操作数使用整数除法/取模；
- `div/mod` 的右操作数为 0 时产生 trap；
- `eq/lt` 返回 `0` 或 `1`；
- `ret x` 表示正常终止并输出 `x`。

这意味着：

- NuSMV 找到的 counterexample 是有限模型内真实存在的语义不一致；
- NuSMV 全部性质通过，只能说明当前有限域和步数界限下没有发现不一致；
- 这不是完整 64-bit 语义下的数学证明。

## 3. TAC 语言

### 3.1 函数格式

```tac
func main(i64 a, i64 b) -> i64
  t0 = add a, b
  ret t0
end
```

参数格式为 `type name`。当前工具主要关注单函数程序。

### 3.2 直线代码指令

```tac
v = const N
v = copy x
v = add x, y
v = sub x, y
v = mul x, y
v = div x, y
v = mod x, y
v = neg x
v = eq x, y
v = lt x, y
ret x
```

### 3.3 CFG 指令

```tac
label:
jmp label
br cond, label_true, label_false
```

当前 v2 CFG 支持 basic block、显式跳转、条件分支和 fallthrough。Phi 节点暂不支持，因此在分支汇合处使用同名变量时，语义相当于普通可变 TAC 变量，而不是 SSA phi。

## 4. Parser 与结构校验

解析器不仅把文本转为 IR，还执行若干结构校验：

- 函数头格式必须合法；
- 参数名不能重复；
- label 不能重复；
- `jmp` / `br` 目标必须存在；
- terminator 之后不能继续出现普通指令；
- 使用的参数必须存在；
- 临时变量必须先定义再使用；
- CFG 边和 predecessor/successor 信息会在解析后重建。

这些检查的目的不是构建完整类型系统，而是尽早把常见建模错误转化为可读的 `ParseError`，避免后续解释器、pass 或 SMV generator 抛出难理解的 `KeyError`。

## 5. 优化 pass 设计

### 5.1 `const-fold`

常量折叠会把所有操作数均为常量的表达式直接替换为 `const`。例如：

```tac
t0 = const 1
t1 = const 2
t2 = add t0, t1
```

可优化为：

```tac
t2 = const 3
```

实现中采用 block-local 常量环境，遇到变量重定义时会 kill 旧常量信息，避免把旧值错误传播到新定义之后。

### 5.2 `const-prop`

常量传播会把已知常量替换进后续表达式：

```tac
t0 = const 1
t1 = add t0, a
```

变成：

```tac
t1 = add 1, a
```

同样，变量被非 const 指令重定义后，旧常量信息会失效。

### 5.3 `dce`

Dead Code Elimination 删除不影响返回值的纯计算。但 `div` / `mod` 可能 trap，因此即使结果未被使用也不能简单删除。例如：

```tac
t0 = div a, a
dead = const 3
ret dead
```

当 `a = 0` 时，原程序会 trap。如果删除 `div`，语义会改变。因此 DCE 保留可能 trap 的指令。

### 5.4 `local-cse`

Local Common Subexpression Elimination 在同一 basic block 内复用已经计算过的表达式：

```tac
t0 = add a, b
t1 = add a, b
```

可变成：

```tac
t1 = copy t0
```

如果表达式依赖的变量或保存结果的变量被重新定义，已有表达式信息会失效。例如 `x` 被赋新值后，任何依赖旧 `x` 的表达式不能继续复用。

### 5.5 `branch-fold` 与 `unreachable-elim`

`branch-fold` 把常量条件分支改写为无条件跳转：

```tac
br 1, then, else
```

变成：

```tac
jmp then
```

`unreachable-elim` 会从 entry 出发删除不可达 block。

### 5.6 `cfg-cp`

`cfg-cp` 是 CFG-aware 的 must-constant propagation。对一个 block 的多个 predecessor，只有当某变量在所有 predecessor 的 out-map 中都存在且值相同时，才认为该变量在当前 block 入口为常量。

这种 meet 策略保守但 sound，适合课程规模 CFG。它避免了“某个分支上是常量，因此在汇合点也误认为是常量”的错误。

### 5.7 `sccp`

当前 `sccp` 是简化版 SCCP-style pipeline：

```text
cfg-cp -> branch-fold -> unreachable-elim
```

它不实现完整 SSA SCCP 的三值 lattice、可达边 worklist 和 phi lattice，但足以展示“常量传播触发分支折叠，再触发不可达块删除”的效果。

## 6. NuSMV Product Machine 建模

生成的 SMV 模型只有一个 `MODULE main`，同时包含源程序和优化程序两份状态：

```text
src_pc, src_done, src_trap, src_out, src_timeout, src_* temporaries
opt_pc, opt_done, opt_trap, opt_out, opt_timeout, opt_* temporaries
```

参数变量是共享的，例如：

```smv
a : 0..7;
init(a) := {0, 1, 2, 3, 4, 5, 6, 7};
next(a) := a;
```

这表示源程序和优化程序在同一组非确定输入上执行。

### 6.1 PC 编码

每条 TAC 指令被 flatten 为一个整数 pc。`pc = N` 表示越过最后一条指令的终止状态。`label:` 会映射到对应 pc，`jmp` 和 `br` 通过 label map 转移。

### 6.2 同步小步执行

每个 SMV transition 中，source 和 optimized 都最多前进一步。如果某一侧已经 `done`、`trap` 或 `timeout`，该侧状态保持不变，另一侧可以继续执行。

这样可以比较“最终行为”，而不要求两侧优化前后指令数量完全一致。

### 6.3 Trap 与 timeout

- 当前执行指令为 `div/mod` 且右操作数为 0 时，设置对应 `trap`；
- 超过 `max_steps` 且尚未结束/陷入 trap，则设置 `timeout`；
- `NoTimeout` 性质用于确保当前模型中没有超步执行。

## 7. CTL 验证性质

生成的模型包含以下 CTL properties：

| 名称 | 含义 |
|---|---|
| `BothEventuallyStop` | 源程序和优化程序最终都 normal stop 或 trap |
| `SameNormalOutput` | 如果二者都正常结束，则输出相同 |
| `SameTrapBehavior1` | 如果源程序 trap，则优化程序最终也 trap |
| `SameTrapBehavior2` | 如果优化程序 trap，则源程序最终也 trap |
| `NoMismatchAtStop` | 二者都停止后，要么都正常且输出相同，要么都 trap |
| `NoTimeout` | 不应出现 timeout |

对于 pass correctness，最关键的是 `NoMismatchAtStop`、两个 trap behavior 和 `SameNormalOutput`。

## 8. 反例解析

CLI 在 `--run-nusmv` 成功执行后，会把 NuSMV 原始日志保存到 `generated/logs/<case>.log`，并默认生成 Markdown 摘要：

```text
generated/counterexamples/<case>.md
```

摘要包括：

- 每条 property 的 PASS/FAIL；
- 失败 property 列表；
- counterexample trace 中的输入、pc、done/trap/out/timeout 等关键状态。

这能直接服务课程实验报告中的“反例或结果分析”部分。

## 9. 测试策略

项目现在使用三类测试互补提高可信度。

### 9.1 单元测试

检查 parser、interpreter、pass 局部行为和 SMV 文本片段。

### 9.2 有限域差分测试

`tests/helpers.py` 中的 `assert_equiv_on_finite_domain` 会枚举所有参数输入，分别解释执行 source 和 optimized，然后比较：

```text
(done, trap, out, timeout)
```

这不是模型检查，但能在没有 NuSMV 的环境中快速发现 pass bug。

### 9.3 SMV 生成回归测试

检查输入初始化是否覆盖完整有限域，临时变量在 source/optimized 两侧是否正确加 `src_` / `opt_` 前缀，避免生成引用错误变量的模型。

## 10. 典型实验流程

### 10.1 正确优化验证

```bash
python -m src.cli.run examples/v1_straightline/cf_01.tac \
  --passes const-fold,const-prop,dce \
  --value-max 7 --max-steps 32 \
  --emit-opt generated/tac/cf_01.opt.tac \
  --emit-smv generated/smv/cf_01.smv \
  --run-nusmv
```

实验报告中建议记录：

- 源程序；
- 优化 pass 序列；
- 优化后程序；
- `VALUE_MAX` 与 `max_steps`；
- 每条 CTL property 的结果；
- 若全部通过，说明在当前有限模型下未发现不一致。

### 10.2 错误优化反例

```bash
make verify-bad
```

`div-self-to-one` 会把 `x / x` 错误替换为 `1`。当 `x = 0` 时，源程序应 trap，而优化程序正常返回 1，因此 NuSMV 应该给出 counterexample。

## 11. 扩展建议

后续可以继续扩展：

1. **SSA 与 phi 节点**：更接近真实编译器 IR，也能实现更标准的 SCCP。
2. **循环建模**：加入 bounded unrolling 或 ranking/timeout 分析。
3. **更多算术语义**：区分 signed/unsigned、overflow、poison/undef。
4. **更强反例解释**：把 trace 映射回 TAC 指令和源代码行。
5. **CI 集成 NuSMV**：在可安装 NuSMV 的 runner 上自动运行模型检查。
6. **报告自动生成**：根据 source/opt/model/log 自动生成实验表格和结论段落。

## 12. 当前边界

- 不支持内存、数组、函数调用和副作用；
- 不支持 phi；
- v2 CFG 假设课程规模、主要是 loop-free 示例；
- 验证范围受 `VALUE_MAX` 和 `max_steps` 影响；
- pass 的 correctness 不是一般性证明，而是通过有限域差分测试和 NuSMV translation validation 共同提高可信度。
