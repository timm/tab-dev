function slow.all(    tr,te,y,i,lo,m1,m2,d,err,n) --> nil
  tr, te, y = halves()
  i  = Tree(tr, tr.rows, y)
  assert(i.n == #tr.rows, "root holds every training row")
  lo = y(i.row)
  for _, row in order(tr.rows) do          -- the payload is the best
    assert(y(row) >= lo - 1e-6, "payload is not the best row") end
  d = 0
  for n in i:walk() do d = max(d, n.lvl) end
  assert(d <= the.depth, "tree grew past depth")
  for _, row in order(te.rows) do          -- every row reaches a
    assert(i:pick(row).row, "a row reached no payload") end -- leaf
  err = function(fn)                      -- mean error of a guess
          return nums(te.rows, function(row)
                   return abs(y(row) - fn(row)) end).mu end
  m1 = err(function(row) return i:pick(row).mu end)
  m2 = err(function() return i.mu end)
  print("tree", m1, "grand mean", m2, "depth", d)
  assert(m1 < m2, "tree lost to the grand mean")
  n = least()                              -- what every cut runs on
  for _, v in ipairs{3, 9, 1, 5} do n(v, "row" .. v) end
  assert(n() == "row1" and select(2, n()) == 1)
  assert(least()() == nil)                 -- offered nothing, holds
  print"PASS tree" end
