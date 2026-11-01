function versus(kind,who1,who2,what,big,    w,t,l,ma,mb,xs,ys)
  w, t, l, ma, mb = 0, 0, 0, {}, {}
  for _, dir in order(dirs(kind)) do
    xs, ys = readcol(dir, who1, what), readcol(dir, who2, what)
    if xs and ys then
      ma[#ma+1], mb[#mb+1] = mid(xs), mid(ys)
      if Same(xs, ys):ok()             then t = t + 1
      elseif (mid(xs) > mid(ys)) == big then w = w + 1
      else                                  l = l + 1 end end end
  print(("%-11s %-10s %7.3f   %-10s %7.3f   %d win %d tie %d loss")
        :format(kind, who1, mid(ma), who2, mid(mb), w, t, l)) end
