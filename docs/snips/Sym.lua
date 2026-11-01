function Sym(txt,at) --> SYM; a SYM for `txt:str` at `at:num`: a-z names,
  return new(SYM, {txt = txt or "S", at = at or 0, n = 0, has = {}}) end
