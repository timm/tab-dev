function mae(model,te,y,    num)    -- mean error of model's guesses
  num = Num()
  for _, row in order(te.rows) do
    num:add(abs(model:guess(row) - y(row))) end
  return num.mu end
