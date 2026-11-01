function pair(tbl,s,    tr,te)      -- rep s's halves of tbl, by seed
  the.seed = 1234567891 + s
  tr, te = tbl:split()
  return tbl:clone(tr), tbl:clone(te) end
