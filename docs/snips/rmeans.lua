function Rmeans(tbl,rows,y,    sub,all,i) --> RMEANS; one BINS per x column
  sub = tbl:clone(rows)
  all = nums(sub.rows, y)
  i   = new(RMEANS, {all = all, has = {}, cols = sub.x})
  for _, col in order(sub.x) do
    i.has[col.at] = Bins(col, sub.rows, y, all) end
  return i end
