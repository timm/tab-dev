function SAME.cliffs(i,    xs,ys,gt,lt,j,k) --> num; how often `i.xs` is in
  xs, ys, gt, lt, j, k = i.xs, i.ys, 0, 0, 0, 0
  for _, x in order(xs) do
    while j < #ys and ys[j+1] <  x do j = j + 1; k = j end
    while k < #ys and ys[k+1] == x do k = k + 1 end
    gt, lt = gt + j, lt + #ys - k end
  return abs(gt - lt) / (#xs * #ys) end
