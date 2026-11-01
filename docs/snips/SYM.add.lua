function SYM.add(i,v,inc) --> value; add one more `v:value` to `i`'s counts.
  if v == "?" then return v end
  inc = inc or 1
  i.n = i.n + inc
  i.has[v] = (i.has[v] or 0) + inc
  if i.has[v] <= 0 then i.has[v] = nil end
  return v end
