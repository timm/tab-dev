-- Does the simple cut pick the same split as the optimized one?
local tab  = dofile("/Users/timm/gh/tab/tab.lua")
local cut2 = dofile(os.getenv("S").."/cut2.lua")(tab)
local same, diff, n = 0, 0, 0
local bad = {}
for _, f in ipairs(arg) do
  local ok, t = pcall(tab.Tab, f)
  if not ok then print("SKIP "..f) goto next end
  -- the whole table, then each half, so nested nodes get tested too
  local cuts = {}
  local a, b = tab.TAB.split(t)
  for _, rows in ipairs{t.rows, a, b} do
    local r1 = tab.TAB.cut(t, rows, 0)
    local r2 = cut2(t, rows, 0)
    n = n + 1
    local s1 = r1 and (r1.col.txt.."|"..tostring(r1.v)) or "nil"
    local s2 = r2 and (r2.col.txt.."|"..tostring(r2.v)) or "nil"
    local hit = s1 == s2
    if not hit and r1 and r2 and r1.col == r2.col and type(r1.v)=="number" and type(r2.v)=="number" then
      hit = math.abs(r1.v - r2.v) < 1e-9          -- same column, same edge
    end
    if hit then same = same + 1 else
      diff = diff + 1
      bad[#bad+1] = string.format("%-22s %s  vs  %s", f:gsub(".*/",""), s1, s2)
    end
  end
  ::next::
end
print(string.format("cuts=%d same=%d diff=%d", n, same, diff))
for i = 1, math.min(#bad, 12) do print("  "..bad[i]) end
