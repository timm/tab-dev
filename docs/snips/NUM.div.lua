function NUM.div(i) --> num; `i`'s standard deviation.
  return i.n < 2 and 0 or sqrt(max(i.m2, 0) / (i.n - 1)) end
