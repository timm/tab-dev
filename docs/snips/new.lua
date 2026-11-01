function new(meta,i) --> inst; connect instance `i` to its class `meta`;
  meta.__index, meta.it, meta.__tostring = meta, meta, o
  return setmetatable(i, meta) end
