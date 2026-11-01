function NODE.walk(i,    todo) --> fun; an iterator over `i` and everything
  todo = {i}
  return function(    n)
    n = table.remove(todo)
    if not n then return end
    if n.at then todo[#todo+1] = n.right; todo[#todo+1] = n.left end
    return n end end
