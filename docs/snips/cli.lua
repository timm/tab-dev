function cli(    k,v) --> dict; update `the` from the command line: a flag,
  for _, s in order(arg) do        -- name=value, action, file
    k, v = s:match"^(%a%w*)=(.*)$"
    if     k               then the[k] = values(v)[1]
    elseif fast[s] or slow[s] then (fast[s] or slow[s])()
    else                       the.file = s end end
  return the end
