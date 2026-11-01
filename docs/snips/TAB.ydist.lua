function TAB.ydist(i,row,    fn) --> num; `row`'s distance to heaven over
  fn = function(col)
          return abs(col:norm(row[col.at]) - col.w) ^ the.p end
  return (sum(i.y, fn) / #i.y) ^ (1 / the.p) end
