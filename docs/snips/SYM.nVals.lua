function SYM.nVals(i,    fn) --> int; how many values `i` has seen, at
  i.kinds = i.kinds or max(2, sum(i.has, function() return 1 end))
  return i.kinds end
