function BAG.score(i,    k,pd,pf,d2h,r1,f1,d1) --> num; `i`'s macro acc
  k, pd, pf, d2h = 0, 0, 0, 0
  for x in pairs(i.want) do
    r1, f1, d1 = i:score1(x)
    k, pd, pf, d2h = k + 1, pd + r1, pf + f1, d2h + d1 end
  return 100*i.ok/i.n, 100*pd/k, 100*pf/k, d2h/k, k end
