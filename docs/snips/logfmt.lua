function logfmt(d,indent,    pad,u,flat,out) --> str
  pad, u, flat, out = ("  "):rep(indent or 0), {}, {}, {}
  for k in pairs(d) do u[#u + 1] = k end
  sort(u)
  for _, k in order(u) do
    if type(d[k]) ~= "table" then
      flat[#flat + 1] = k .. "=" .. o(d[k]) end end
  if #flat > 0 then out[1] = pad .. table.concat(flat, " ") end
  for _, k in order(u) do
    if type(d[k]) == "table" then
      out[#out + 1] = pad .. k
      out[#out + 1] = logfmt(d[k], (indent or 0) + 1) end end
  return table.concat(out, "\n") end
