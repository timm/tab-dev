function SAME.cohen(i,  a,b,sd) --> num; pooled sds.
  a, b = nums(i.xs), nums(i.ys)
  sd = sqrt(((a.n-1) * a:div()^2 + (b.n-1) * b:div()^2) / (a.n+b.n-2))
  return abs(a.mu - b.mu) / (sd + 1e-32) end
