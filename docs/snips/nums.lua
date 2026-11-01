function nums(lst,fn,    i) --> NUM; one NUM summarizing `fn(x)` over
  fn = fn or same
  i=Num(); for _,x in order(lst) do i:add(fn(x)) end; return i end
