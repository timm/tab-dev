function TAB.clone(i,rows,how,    out) --> TAB; `rows` in a fresh TAB
  out = {how and map(i.cols, function(col) return col.txt:lower() end)
             or i.names}
  for _, row in order(rows or {}) do
    out[#out + 1] = not how and row or map(i.cols,
      function(col) return col[how](col, row[col.at]) end) end
  return Tab(out) end
