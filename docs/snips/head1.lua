function head1(rows,n,    out)      -- rows' first n, or all of them
  out = {}
  for j = 1, (#rows < n and #rows or n) do out[j] = rows[j] end
  return out end
