-- cmp.lua: rmeans and tree, side by side, one rep per set.
-- usage: luajit etc/cmp.lua ~/gits/moot/optimize/*/*.csv
--        TAB=~/gh/tab luajit etc/cmp.lua $MOOT/optimize/*/*.csv
tab = (os.getenv"TAB" or "../tab"):gsub("^~", os.getenv"HOME" or "~")
package.path = tab .. "/?.lua;" .. package.path
local T = require "tree"
if setfenv then setfenv(1, T) end
local _ENV = T
the = cli()

function rank(te,y,g,    ys,rows,lo)   -- tab-eg's top(), on any g
  ys, rows = {}, {}
  for n, row in order(te.rows) do ys[n], rows[n] = y(row), row end
  for n, row in order(rows, function(a,b) return g[a] < g[b] end) do
    if n > the.check then break end
    lo = (not lo or y(row) < lo) and y(row) or lo end
  for n, v in order(ys, lt) do
    if v == lo then return 100 * (n-1) / max(1, #ys-1) end end
  return 100 end

function head1(rows,n,    out)
  out = {}
  for j = 1, (#rows < n and #rows or n) do out[j] = rows[j] end
  return out end

function go(file,    tr,te,y,r45,rall,t,gs,out)
  the.file, the.seed = file, 1234567891    -- every set, the same split
  tr, te, y = halves()
  r45  = Rmeans(tr, head1(tr.rows, the.budget - the.check), y)
  rall = Rmeans(tr, tr.rows, y)
  -- STALE: `Tree` grows over a klass only now -- `y` here is `ydist`,
  -- a distance, which it never really supported (its own comment said
  -- so).  Left broken on purpose rather than quietly given a klass it
  -- was not asked for.  Use `Rmeans` for a continuous target.
  t    = Tree(tr, tr.rows, y)
  out  = {}
  for _, a in ipairs{{"rmeans45", function(row) return r45:guess(row) end},
                     {"rmeansall",function(row) return rall:guess(row) end},
                     {"treeMu",   function(row) return t:guess(row) end},
                     {"treePay",  function(row)
                                    return y(t:pick(row)) end}} do
    gs = {}
    for _, row in order(te.rows) do gs[row] = a[2](row) end
    out[#out+1] = ("%6.1f %7.4f"):format(rank(te,y,gs),
                                         mae(te.rows, y, a[2])) end
  print(("%-28s %s"):format(file:match"([^/]+)%.csv$",
                            table.concat(out, "  "))) end

print(("%-28s %13s %15s %15s %15s"):format("set", "rmeans45",
      "rmeansall", "treeMu", "treePay"))
print(("%-28s %s"):format("", "  rank     mae    rank     mae"
      .. "    rank     mae    rank     mae"))
for _, f in ipairs(arg) do
  if f:find"%.csv$" then
    ok, err = pcall(go, f)
    if not ok then
      io.stderr:write(f, ": ", tostring(err), "\n") end end end
