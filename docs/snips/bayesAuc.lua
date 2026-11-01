function bayesAuc(tr,te,    trb,nb,col,rows,post,t,sum,k,a) -- macro mean
  trb     = tr:clone(tr.rows, "bin")
  nb, col = Nb(trb, trb.rows), trb.klass
  rows, post = tr:clone(te.rows, "bin").rows, {}
  for _, row in order(rows) do post[row] = nb:posts(row) end
  sum, k = 0, 0
  for x in pairs(nb.subs) do
    t = {}
    for _, row in order(rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    a = auc(t)
    if a then sum, k = sum + a, k + 1 end end
  return ("%.4f,%d"):format(k > 0 and sum / k or 0, k) end
