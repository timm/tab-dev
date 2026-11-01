function NB.like(i,sub,row,    fn) --> num; log P(`row` | `sub:TAB`)
  fn = function(col1,at,    col,v)
        col, v = i.tbl.x[at], row[col1.at] -- col knows every value;
        if v == "?" then return 0 end      -- col1 knows this klass's
        return log(((col1.has[v] or 0) + the.m)    -- and m per value
                   / (col1.n + the.m * col:nVals())) end
  return log((#sub.rows + the.m) / (i.n + the.m * i.nKlass)) -- m/klass
         + sum(sub.x, fn) end
