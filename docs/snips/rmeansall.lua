function rmeansall(tr,te,    y)     -- the rich arm: every train row
  y = goal(tr)
  return score(Rmeans(tr, tr.rows, y), te, y) end
