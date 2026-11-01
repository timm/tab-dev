function TAB.split(i,    rows,n,t,u1,u2) --> list; two lists, 80:20, of a
  rows   = shuffle(map(i.rows, same))    -- never i.rows itself
  n      = floor(.8 * #rows)
  u1, u2 = {}, {}; t = u1
  for j,row in order(rows) do if j>n then t = u2 end; t[#t+1] = row end
  return u1, u2 end
