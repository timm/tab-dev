function halves(    tbl,tr,te) --> TAB; `the.file` as train and test TABs,
  tbl    = Tab(the.file)
  tr, te = tbl:split()
  tr, te = tbl:clone(tr), tbl:clone(te)
  return tr, te, function(row) return tr:ydist(row) end end
