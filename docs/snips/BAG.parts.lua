function BAG.parts(i,x,    tp,fp,fn) --> int; klass `x:value`'s tp, fp, fn
  tp = i.hit[x] or 0
  fp = (i.got[x] or 0) - tp
  fn = (i.want[x] or 0) - tp
  return tp, fp, fn, i.n - fn - fp - tp end
