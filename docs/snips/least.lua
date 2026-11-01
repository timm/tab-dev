function least(    it,b4) --> fun; a collector of the least thing it is
  return function(score,payload)
    if score ~= nil and (b4 == nil or score < b4) then
      it, b4 = payload, score end
    return it, b4 end end
