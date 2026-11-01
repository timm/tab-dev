function sum(t,fn,    n) --> num; `fn(v,k)` over every item of `t`, added
  n=0; for k, v in pairs(t) do n = n + fn(v, k) end; return n end
