function home(f)                    -- cache dir, mirroring moot's tree
  return cache .. "/" ..
         (f:match"moot/(.+)%.csv$" or f:match"([^/]+)%.csv$") end
