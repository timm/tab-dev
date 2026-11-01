function Num(txt,at) --> NUM; a NUM for `txt:str` at `at:num`: A-Z num, !+-
  return new(NUM, {txt = txt or "N", at = at or 0, n = 0, mu = 0, m2 = 0,
                   w = (txt or ""):find"%-$" and 0 or 1}) end
