function NODE.cut(i,    out,xy,x,tot,d,b,lhs,val,big) --> dict; cut of
  function val(a,b)  return (a:div()*a.n + b:div()*b.n) / (a.n+b.n) end
  function big(lo,n) return the.leaf <= lo and lo <= n - the.leaf end
  out = least()                      -- least diversity left behind
  for _, col in order(i.sub.x) do
    xy, tot = {}, i.Y()            -- y is already paid for; one
    for _, row in order(i.rows) do -- pass fills xy and sums it
      x = row[col.at]
      if x ~= "?" then xy[#xy+1] = {x=x, y=tot:add(i.ys[row])} end end
    if col.it == SYM then
      d = {}
      for _, p in order(xy) do
        b = d[p.x] or i.Y(); b:add(p.y); d[p.x] = b end
      for v, lhs in pairs(d) do
        if big(lhs.n, #xy) then
          out(val(lhs, tot - lhs), {col = col, bin = v}) end end
    else
      sort(xy, "x")
      lhs = i.Y()
      for j, p in order(xy) do
        lhs:add(p.y)
        if j < #xy and p.x ~= xy[j+1].x and big(j, #xy) then
          out(val(lhs,tot-lhs),{col=col,bin=p.x}) end end end end
  return (out()) end
