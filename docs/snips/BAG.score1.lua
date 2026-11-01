function BAG.score1(i,x,    tp,fp,fn,tn,r1,f1) --> num; klass `x:value`'s
  tp, fp, fn, tn = i:parts(x)
  r1 = tp / (tp + fn)
  f1 = fp + tn > 0 and fp / (fp + tn) or 0
  return r1, f1, sqrt((1 - r1) ^ 2 + f1 ^ 2) / sqrt(2) end
