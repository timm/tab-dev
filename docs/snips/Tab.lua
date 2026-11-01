function Tab(src,    i) --> TAB; a TAB from `src`: a file name, or names
  i = new(TAB, {rows = {}})
  for _, row in order(type(src) == "string" and csv(src) or src) do
    i:addRow(row) end
  return i end
