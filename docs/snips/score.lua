function score(model,te,y)          -- where its top 5 sat, and its mae
  return ("%.3f,%.6g"):format(top(model, te, y), mae(model, te, y)) end
