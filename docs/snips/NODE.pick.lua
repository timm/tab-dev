function NODE.pick(i,row,    c) --> NODE; leaf `row` falls into: its `mu`
  if not i.at then return i end
  c = i.at
  return (c.col:holds(row[c.col.at], c.bin) and i.left or i.right)
         :pick(row) end
