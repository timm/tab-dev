function csv(file,   rows,s) --> rows; `rows` in a `file:str`.
  rows = {}
  for line in io.lines((file:gsub("^~", os.getenv"HOME" or "~"))) do
    s = line:match"^%s*(.-)%s*$"
    if s ~= "" and s:sub(1, 1) ~= "#" then
      rows[#rows + 1] = values(s) end end
  return rows end
