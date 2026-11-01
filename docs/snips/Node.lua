function Node(tbl,rows,y,lvl,Y,    i,v,pay,all,cut,a,b,t,op) --> NODE; one
  i   = new(NODE, {tbl = tbl, rows = rows, y = y, lvl = lvl, Y = Y,
                   n = #rows, sub = tbl:clone(rows), ys = {}, txt = ""})
  all, pay = Y(), Y == Num and least()   -- a klass has no best row
  for _, row in order(rows) do
    v = y(row); i.ys[row] = v; all:add(v)
    if pay then pay(v, row) end end
  i.all = all
  i.row = pay and pay()
  i.mu  = all.mu or best(all.has, same)   -- a mean, or a majority
  cut = i.n >= 2*the.leaf and lvl < the.depth and i:cut()
  if cut then
    a, b = {}, {}
    for _, row in order(rows) do
      t = cut.col:holds(row[cut.col.at], cut.bin) and a or b
      t[#t + 1] = row end
    if #a >= the.leaf and #b >= the.leaf then   -- else, a bad cut
      i.at = cut
      i.left  = Node(tbl, a, y, lvl+1, Y)
      i.right = Node(tbl, b, y, lvl+1, Y)
      op = cut.col.it == SYM and {"==", "~="} or {"<=", ">"}
      i.left.txt  = cut.col.txt.." "..op[1].." "..o(cut.bin)
      i.right.txt = cut.col.txt.." "..op[2].." "..o(cut.bin) end end
  return i end
