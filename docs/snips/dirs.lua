function dirs(kind,    out,h)       -- every cached set of this kind
  out, h = {}, io.popen("find " .. cache .. "/" .. (kind or "") ..
                        " -name '*.csv' 2>/dev/null")
  for line in h:lines() do out[line:match"^(.*)/"] = true end
  h:close()
  return sorted(out) end
