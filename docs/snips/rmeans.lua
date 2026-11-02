function Rmeans(tbl,rows,y, --> RMEANS; per x column, its bins' y means
                sub,all,i,bins,b,w,fn)  -- and the variance they cut
  sub = tbl:clone(rows)
  all = nums(sub.rows, y)
  i   = new(RMEANS, {all = all, has = {}, cols = sub.x})
  for _, col in order(sub.x) do
    bins = {}
    for _, row in order(sub.rows) do
      b = col:bin(row[col.at])
      bins[b] = bins[b] or Num()
      bins[b]:add(y(row)) end
    fn = function(v) return v.n/all.n * v:div() ^ 2 end
    w  = all:div() ^ 2 - sum(bins, fn)
    i.has[col.at] = {bins = bins, w = max(0, w)} end
  return i end
