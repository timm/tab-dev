function Bins(col,rows,y,all,    i,b) --> BINS; `col`'s bins over `rows`
  i = new(BINS, {has = {}, w = 0})
  for _, row in order(rows) do
    b = col:bin(row[col.at])
    i.has[b] = i.has[b] or Num()
    i.has[b]:add(y(row)) end
  i.w = i:weight(all)
  return i end
