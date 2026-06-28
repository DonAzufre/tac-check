func main(i64 a) -> i64
  t0 = const 1
  t1 = const 2
  t2 = add t0, t1
  dead = mul t2, t2
  ret t2
end
