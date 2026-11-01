function mid(xs,    ys)             -- the median of xs
  ys = sort(map(xs, same))
  return #ys == 0 and 0 or (#ys % 2 == 1 and ys[(#ys+1)/2]
                            or (ys[#ys/2] + ys[#ys/2+1]) / 2) end
