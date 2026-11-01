function ktree(tr,    trb,k,d,was,i) --> NODE, TAB
  trb  = tr:clone(tr.rows, "bin")
  k, d = trb.klass:nVals(), 2
  while 2^(d-1) < k do d = d + 1 end
  was, the.depth = the.depth, max(the.depth, d + 1)
  i    = Tree(trb, trb.rows,
              function(row) return row[trb.klass.at] end, Sym)
  the.depth = was
  return i, trb end
