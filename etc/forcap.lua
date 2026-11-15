-- forcap.lua: `fornumall` with each tree held to CAP rows.
--
-- usage: luajit etc/forcap.lua cap f.csv     (TAB=../tab, CACHE=./cache)
--        writes <cache>/<set>/forcap<cap>.csv, rank,win,mae per rep
--        TREES=1 luajit etc/forcap.lua cap f.csv   -> treecap<cap>.csv
--
-- The regression forest that `fornumall` scores draws, for each of
-- its 30 trees, a bootstrap as large as the training set.  This is
-- that forest with one number changed: each tree draws CAP rows, or
-- all of them when the set holds fewer.  Everything else is
-- tab-eg.lua's own -- `goal`, `binTab`, `leafmean`, `score`, and
-- `scored`, which hands over the same seeded splits every other arm
-- was scored on -- so an arm written here differs from `fornumall`
-- by the rows a tree sees and by nothing else.
--
-- Check: with CAP above the set's size this must reproduce
-- `fornumall` to the digit, because it then makes the very same
-- draws in the very same order.
--
-- TREES=1 is the control for "does the forest earn its 30 trees at
-- this budget": ONE tree, on CAP distinct rows (a lone tree has no
-- use for a bootstrap's repeats), looking at every column at every
-- split (sqrt-of-columns is there to make a forest's trees differ,
-- and one tree has no one to differ from).
package.path = (os.getenv "TAB" or "../tab") .. "/?.lua;" .. package.path
local tab = require "tab"
require "tab-eg"                   -- its functions land in `tab`
local cap, file = tonumber(arg[1]), arg[2]
local trees = tonumber(os.getenv "TREES") or tab.the.rounds
local one   = trees == 1
tab.the.file = file                -- `goal` reads the path for its kind

local function fornumcap(tr, te)
  local y   = tab.goal(tr)
  local tbl = tab.binTab(tr, tr.rows, y)
  local fst = tab.Forest(tbl, tbl.rows, 0)      -- no trees yet
  local c   = one and 0 or math.max(1, math.floor(math.sqrt(#tbl.x)))
  local n   = math.min(cap, #tbl.rows)
  for k = 1, trees do
    local rows
    if one then
      local all = tab.shuffle(tab.map(tbl.rows, tab.same))
      rows = {}
      for j = 1, n do rows[j] = all[j] end
    else rows = tab.some(tbl.rows, n) end
    fst.all[k] = tab.Tree(tbl, rows, 1, c) end
  return tab.score({guess = function(_, row)
    local s, m = 0, 0
    for _, t in ipairs(fst.all) do
      local v = tab.leafmean(t:pick(row), y)
      if v then s, m = s + v, m + 1 end end
    return m > 0 and s / m or 0 end}, te, y) end

local who = os.getenv "WHO" or ((one and "treecap" or "forcap") .. cap)
print(tab.scored(file, who, fornumcap, "rank,win,mae"))
