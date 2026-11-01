function SYM.div(i,    fn) --> num; `i`'s entropy.
  fn = function(n) return -n/i.n * log(n/i.n) end
  return sum(i.has, fn) / log(2) end
