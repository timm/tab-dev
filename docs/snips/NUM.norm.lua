function NUM.norm(i,v,    z) --> value; `v:value` on a logistic cdf, clipped
  if v == "?" then return v end
  z = (v - i.mu) / (i:div() + 1e-32)
  z = z > 3 and 3 or (z < -3 and -3 or z)
  return 1 / (1 + exp(-1.7 * z)) end
