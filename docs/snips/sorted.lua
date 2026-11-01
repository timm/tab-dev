function sorted(t,    u)            -- t's keys, in order
  u = {}
  for k in pairs(t) do u[#u + 1] = k end
  return sort(u) end
