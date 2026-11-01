function Tree(tbl,rows,y,Y) --> NODE; a tree over `rows` of `tbl:TAB`,
  return Node(tbl, rows or tbl.rows,
                   y or function(row) return tbl:ydist(row) end,
                   1, Y or Num) end
