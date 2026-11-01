function shuffle(t,    j) --> list; `t`, Fisher-Yates shuffled in place.
  for k = #t, 2, -1 do j = rint(k); t[k], t[j] = t[j], t[k] end
  return t end
