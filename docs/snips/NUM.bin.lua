function NUM.bin(i,v,    b) --> value; `v:value`'s bin, 1..`the.bins`.
  if v == "?" then return v end
  b = 1 + floor(the.bins * i:norm(v))
  return b > the.bins and the.bins or b end
