function SAME.ks(i,    xs,ys,p,q,d,v) --> num; widest gap of two cdfs
  xs, ys, p, q, d = i.xs, i.ys, 0, 0, 0
  while p < #xs and q < #ys do
    v = min(xs[p+1], ys[q+1])
    while p < #xs and xs[p+1] == v do p = p + 1 end
    while q < #ys and ys[q+1] == v do q = q + 1 end
    d = max(d, abs(p/#xs - q/#ys)) end
  return d / sqrt((#xs + #ys) / (#xs * #ys)) end
