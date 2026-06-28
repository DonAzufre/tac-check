func main(i64 a) -> i64
entry:
  t0 = const 1
  t1 = const 2
  c0 = eq t0, t1
  br c0, then, else
then:
  t2 = const 5
  ret t2
else:
  t2 = const 6
  ret t2
end