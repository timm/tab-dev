function auc(t,    ps,ns,u,j,k,tot) --> num; chance a random positive
  ps, ns = {}, {}                 -- outscores a random negative, given
  for _, p in order(t) do         -- `t`, a list of {score, want:bool}
    u = p[2] and ps or ns; u[#u + 1] = p[1] end
  if #ps == 0 or #ns == 0 then return nil end
  sort(ps); sort(ns)
  j, k, tot = 0, 0, 0             -- cliffs' walk: for each positive,
  for _, x in order(ps) do        -- negatives below, half the ties
    while j < #ns and ns[j+1] <  x do j = j + 1; k = j end
    while k < #ns and ns[k+1] == x do k = k + 1 end
    tot = tot + j + (k - j) / 2 end
  return tot / (#ps * #ns) end
