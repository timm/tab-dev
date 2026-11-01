function map(t,fn,    u) --> list; `fn(v,k)` over `t`, in order, with nils
  u={}; for k, v in ipairs(t) do u[#u+1] = fn(v, k) end 
  return u end                                        
