function BINS.weight(i,all,    fn,s) --> num; how much of `all:NUM`'s
  fn = function(v) return v.n/all.n * v:div() ^ 2 end
  s = all:div() ^ 2 - sum(i.has, fn)
  return s > 0 and s or 0 end
