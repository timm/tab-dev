function slow.tree(    tr,te,y,i) --> nil
  tr, te, y = halves()
  i = Tree(tr, tr.rows, y)
  about()                     -- :config, then :tree -- two sections,
  print"\n:tree"              -- which `,/pretty` draws as a table
  print(logfmt(i:dict())) end
