function NB.posts(i,row,    t,hi,z) --> dict; p(klass | `row`) for every
  t, hi = {}, nil
  for k, sub in pairs(i.subs) do
    t[k] = i:like(sub, row)
    if not hi or t[k] > hi then hi = t[k] end end
  z = 0
  for k, v in pairs(t) do t[k] = exp(v - hi); z = z + t[k] end
  for k, v in pairs(t) do t[k] = v / z end
  return t end
