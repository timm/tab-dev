function NUM.add(i,v,inc,    d) --> value; add `v:value` to `i`, returning
  if v == "?" then return v end
  inc = inc or 1
  i.n = i.n + inc
  if i.n <= 0 then i.n, i.mu, i.m2 = 0, 0, 0; return v end
  d    = v - i.mu
  i.mu = i.mu + inc * d / i.n
  i.m2 = i.m2 + inc * d * (v - i.mu)
  return v end
