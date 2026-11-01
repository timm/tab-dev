function Nb(tbl,rows,    i,col,v) --> NB; one sub-TAB per klass in `rows`
  col = tbl.klass
  i   = new(NB, {tbl = tbl, subs = {}, n = #rows, nKlass = 0})
  for _, row in order(rows) do
    v = row[col.at]
    if not i.subs[v] then
      i.subs[v], i.nKlass = tbl:clone(), i.nKlass + 1 end
    i.subs[v]:addRow(row) end
  return i end
