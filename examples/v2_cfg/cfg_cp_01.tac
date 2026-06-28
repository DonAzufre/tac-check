func main(i64 a) -> i64
entry:
  t0 = const 0
  c0 = eq t0, t0
  br c0, then, else

then:
  t1 = const 2
  ret t1

else:
  t2 = const 3
  ret t2
end
