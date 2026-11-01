function SYM.__sub(i,j,    k,m) --> SYM; what is left of `i` once `j` is
  k = new(SYM, {txt = i.txt, at = i.at, n = i.n - j.n, has = {}})
  for v, n in pairs(i.has) do
    m = n - (j.has[v] or 0)
    if m > 0 then k.has[v] = m end end
  return k end
