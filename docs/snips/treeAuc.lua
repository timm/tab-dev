function treeAuc(tr,te,how,    i,trb,col,rows,post,t,sum,k,a) --> str
  i, trb = ktree(tr)
  col    = trb.klass
  rows   = tr:clone(te.rows, "bin").rows
  post   = {}
  for _, row in order(rows) do post[row] = how(i, row) end
  sum, k = 0, 0
  for x in pairs(col.has) do
    t = {}
    for _, row in order(rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    a = auc(t)
    if a then sum, k = sum + a, k + 1 end end
  return ("%.4f,%d"):format(k > 0 and sum / k or 0, k) end
