function print(...) --> nil; print the lot, tab separated, everything
  local out = {}
  for j = 1, select("#", ...) do out[j] = o((select(j, ...))) end
  io.write(table.concat(out, "\t"), "\n") end
