function TAB.addRow(i,row) --> row; add `row` to `i`.  The first row read
  if not i.cols then return i:head(row) end
  i.rows[#i.rows + 1] = row
  for _, col in order(i.cols) do col:add(row[col.at]) end
  return row end
