func main(i64 a) -> i64
entry:
  t0 = const 1
  br t0, then, else

then:
  t1 = const 3
  ret t1

else:
  t2 = const 4
  ret t2
end
