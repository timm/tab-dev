function BAG.tally(i,want,got) --> nil; add one guess to `i`: `want:value`
  i.n          = i.n + 1
  i.ok         = i.ok + (want == got and 1 or 0)
  i.want[want] = (i.want[want] or 0) + 1
  i.got[got]   = (i.got[got] or 0) + 1
  if want == got then i.hit[got] = (i.hit[got] or 0) + 1 end end
