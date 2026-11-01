function NUM.__sub(i,j,    n,d) --> NUM; what is left of `i` once `j` is
  n = i.n - j.n
  if n < 1 then return Num(i.txt, i.at) end
  d = j.mu - i.mu
  return new(NUM, {txt = i.txt, at = i.at, w = i.w, n = n,
                   mu = (i.n*i.mu - j.n*j.mu) / n,
                   m2 = max(0, i.m2 - j.m2 - d*d*i.n*j.n/n)}) end
