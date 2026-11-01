function sort(t,fn,    k) --> list; `t`, sorted in place, ascending.  `fn`
  if fn and type(fn) ~= "function" then
    k = fn; fn = function(a,b) return a[k] < b[k] end end
  table.sort(t, fn)
  return t end
