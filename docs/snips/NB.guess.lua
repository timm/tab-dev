function NB.guess(i,row,    fn) --> value; `row`'s likeliest klass.
  fn = function(sub) return i:like(sub, row) end
  return (best(i.subs, fn)) end
