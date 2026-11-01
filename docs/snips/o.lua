function o(x,    u) --> str; `x` as text: a fraction through `the.fmt`, a
  if type(x) ~= "table" then              
    if type(x) ~= "number" then return tostring(x) end   
    return tostring(x == floor(x) and floor(x) or the.fmt:format(x)) end
  u = {}
  if #x>0 then for _, v in ipairs(x) do u[#u+1] = o(v) end
          else for k, v in pairs(x) do
                 if k ~= "it" and type(v) ~= "function" then
                   u[#u + 1] = o(k) .. "=" .. o(v) end end end
  return "{"..table.concat(#x > 0 and u or sort(u, lt)," ").."}" end
