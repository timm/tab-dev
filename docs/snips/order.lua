function order(t,fn) --> fun; `ipairs(t)`, or, given `fn`, that of a sorted
  if not fn then return ipairs(t) end
  return ipairs(sort(map(t, same), fn)) end
