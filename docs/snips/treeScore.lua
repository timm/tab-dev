function treeScore(tr,te,how,    i,trb,bag,col) --> str
  i, trb  = ktree(tr)
  bag, col = Bag(), trb.klass
  for _, row in order(tr:clone(te.rows, "bin").rows) do
    bag:tally(row[col.at], how(i, row)) end
  return ("%.1f,%.1f,%.1f,%.3f"):format(bag:score()) end
