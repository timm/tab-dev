function NODE.posts(i,row,    n,t) --> dict; p(klass | `row`) off the leaf
  n, t = i:pick(row), {}
  for k, m in pairs(n.all.has) do t[k] = m / n.all.n end
  return t end
