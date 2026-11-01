function NODE.ycols(i,f,    t) --> str; one cell per y column -- `f(col)`
  t = {}
  for k, col in order(i.sub.y) do
    t[k] = ("%" .. max(10, #col.txt + 2) .. "s"):format(f(col)) end
  return table.concat(t) end
