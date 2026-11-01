function goal(tbl,    col) --> fn; a `fn` that scores one `row`.  For
  col = (the.file or ""):find"/regression/"
        and #tbl.y == 1 and tbl.y[1].it == NUM and tbl.y[1]
  if col then
    return function(row) return tonumber(row[col.at]) or col.mu end end
  return function(row) return tbl:ydist(row) end end
