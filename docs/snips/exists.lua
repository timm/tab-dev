function exists(f,    h)            -- is f a file we can read?
  h = io.open(f)
  if h then h:close() end
  return h ~= nil end
