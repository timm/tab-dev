function NODE.show(i,    t,ends,cell,n) --> nil; print `i`, one line per
  cell = function(col)
    return col.it == NUM and o(col.mu) or best(col.has, same) end
  t, ends = {}, {}
  for n in i:walk() do
    if not n.at then t[#t + 1] = n end end
  sort(t, "mu")
  ends[t[#t]] = " \226\156\151 "            -- cross the worst leaf,
  ends[t[1]]  = " \226\156\147 "            -- tick the best one
  print(("%-26s %5s %6s   %s"):format("", "n", "mu",
        i:ycols(function(col) return col.txt end)))
  for n in i:walk() do
    print(("%-26s %5d %6s%s%s"):format(
            ("|  "):rep(max(0, n.lvl-2)) .. n.txt, -- root gets no bar
            n.n, o(n.mu), ends[n] or "   ", n:ycols(cell))) end
  print"" end
