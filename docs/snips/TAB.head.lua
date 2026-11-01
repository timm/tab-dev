function TAB.head(i,names,    col) --> nil; read `names:row` as `i`'s
  i.names, i.cols, i.x, i.y = names, {}, {}, {}
  for at, txt in order(names) do
    col = Col(txt, at)
    i.cols[#i.cols + 1] = col
    if     txt:find"X$"     then                 -- summarized, skipped
    elseif txt:find"[-+!]$" then i.y[#i.y + 1] = col
      if txt:find"!$" then i.klass = col end  -- last ! is the klass
    else i.x[#i.x + 1] = col end end end
