function NODE.dict(i,    t) --> dict
  t = {n = i.n, mu = i.mu}
  if i.txt ~= "" then t.txt = i.txt end
  for _, col in order(i.sub.y) do
    t[col.txt] = col.it == NUM and col.mu or best(col.has, same) end
  if i.at then
    t.left, t.right = i.left:dict(), i.right:dict() end
  return t end
