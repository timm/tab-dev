function values(s,   u,v) --> row; values from comma-separated `s`.
  u = {}
  for s1 in (s .. ","):gmatch"(.-)," do
    v = s1:match"^%s*(.-)%s*$"
    u[#u + 1] = tonumber(v) or v end
  return u end
