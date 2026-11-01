function RMEANS.guess(i,row,    s,w,bins,v,mu) --> num; `row`'s guess: bin
  s, w, mu = 0, 0, i.all.mu
  for _, col in order(i.cols) do
    bins = i.has[col.at]
    v    = bins and bins.has[col:bin(row[col.at])]
    if v and bins.w > 0 then
      s = s + bins.w * (v.n * v.mu + the.m * mu) / (v.n + the.m)
      w = w + bins.w end end
  if w > 0 then return s / w end
  return i.all.mu end
