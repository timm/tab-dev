-- Same cut, or only a tie broken the other way?  Re-score both
-- winners with ONE scorer, so a disagreement that is really a tie
-- shows up as delta == 0.
local tab  = dofile("/Users/timm/gh/tab/tab.lua")
local cut3 = dofile(os.getenv("S").."/cut4.lua")(tab)
local function rescore(t, rows, r)
  local this, that = tab.Sym(), tab.Sym()
  for _, row in ipairs(rows) do
    local x = row[r.col.at]
    if x ~= "?" then
      local left = (r.col.it == tab.NUM) and (x <= r.v) or (x == r.v)
      ;(left and this or that):add(row[t.klass.at])
    end
  end
  return (this:div()*this.n + that:div()*that.n)/(this.n + that.n)
end
local n, same, tie, real = 0, 0, 0, 0
for _, f in ipairs(arg) do
  local ok, t = pcall(tab.Tab, f); if not ok then goto next end
  tab.seed()                               -- same halves every run
  local a, b = tab.TAB.split(t)
  for _, rows in ipairs{t.rows, a, b} do
    local r1, r2 = tab.TAB.cut(t, rows, 0), cut3(t, rows, 0)
    n = n + 1
    if r1 == nil or r2 == nil then
      if r1 == r2 then same = same + 1 else real = real + 1
        print(("REAL %s one side nil"):format(f:gsub(".*/",""))) end
    elseif r1.col == r2.col and r1.v == r2.v then same = same + 1
    else
      local d = rescore(t, rows, r1) - rescore(t, rows, r2)
      if math.abs(d) < 1e-12 then tie = tie + 1 else
        real = real + 1
        print(("REAL %-20s orig %s|%s vs cut3 %s|%s delta=%.3g"):format(
          f:gsub(".*/",""), r1.col.txt, tostring(r1.v),
          r2.col.txt, tostring(r2.v), d))
      end
    end
  end
  ::next::
end
print(("cuts=%d identical=%d tie=%d REAL=%d"):format(n, same, tie, real))
