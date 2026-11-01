function best(t,fn,    n,m,u) --> any; key of `t` with the biggest
  for k, v in pairs(t) do
    m = fn(v, k)
    if not n or m > n then n, u = m, k end end
  return u, n end
