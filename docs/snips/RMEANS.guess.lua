function RMEANS.guess(i,row,    s,w,it,v,mu) --> num; `row`'s guess: bin
  s, w, mu = 0, 0, i.all.mu
  for _, col in order(i.cols) do
    it = i.has[col.at]
    v  = it and it.bins[col:bin(row[col.at])]
    if v and it.w > 0 then
      s = s + it.w * (v.n * v.mu + the.m * mu) / (v.n + the.m)
      w = w + it.w end end
  if w > 0 then return s / w end
  return i.all.mu end
