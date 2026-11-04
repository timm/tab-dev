#!/usr/bin/env luajit
-- vim: set ts=2 sw=2 sts=2 et cc=75 :
-- forest-eg.lua: the hard-vote forest, scored like every other arm.
--
-- `ens.py hardeep` is this same learner in python: 30 members, each
-- on its own bootstrap, each node redrawing sqrt(#x) columns, depth
-- 12, leaf 2, RAW columns -- no binning, which is the whole point of
-- a tree over a counter.  One vote per member, the majority wins.
-- So the two arms differ in runtime and in nothing else, and a gap
-- between them is a port bug, not a result.
--
-- TABDIR picks which `tab` answers the require.  Point it at a
-- directory holding a compiled tab.lua and the same rig scores the
-- yue build, with no edit here.
--   usage: TABDIR=... luajit etc/forest-eg.lua go=hard file=f.csv
local TABDIR = os.getenv("TABDIR") or (os.getenv("HOME") .. "/gh/tab")
package.path = TABDIR .. "/?.lua;" .. package.path
require "tab"
local tab = require "tab-eg"
if setfenv then setfenv(1, tab) end
local _ENV = tab

usage = [[
flags:
  file=~/gits/moot/classify/diabetes.csv   a table with a klass
]]
for k, v in usage:gmatch"\n%s+(%a+)=(%S+)" do the[k] = values(v)[1] end

-- The knobs ens.py sets around its fit, set here instead of trusted
-- to the defaults: an arm that reads its depth from whatever the
-- library last shipped is not a comparison, it is a coincidence.
function forest(tr,    was,i) --> FOREST
  was = {the.depth, the.leaf, the.rounds}
  the.depth, the.leaf, the.rounds = 12, 2, 30
  i = Forest(tr, tr.rows)
  the.depth, the.leaf, the.rounds = was[1], was[2], was[3]
  return i end

-- ---- scoring ---------------------------------------------------------
-- One fit, both answers.  `scored` writes a single csv, so an arm
-- that wants acc AND auc through it pays for a second forest that
-- can only agree with the first -- half the night, for nothing.
-- `ens.py` fits once and writes both; so does this.
function scored2(file,who,fun,    dir,fa,fb,tbl,ha,hb,t0,secs,ok,a,b)
  dir = home(file)
  fa, fb = dir.."/"..who..".csv", dir.."/"..who.."auc.csv"
  if exists(fa) and exists(fb) and not the.force then return fa end
  os.execute("mkdir -p " .. dir)
  tbl = Tab(file)
  ha, hb = io.open(fa, "w"), io.open(fb, "w")
  ha:write("rep,secs,acc,pd,pf,d2h\n")
  hb:write("rep,secs,auc,klasses\n")
  for s = 1, reps do
    t0 = os.clock()
    ok, a, b = pcall(fun, pair(tbl, s))
    if not ok then
      ha:close(); hb:close(); os.remove(fa); os.remove(fb)
      error(a, 0) end
    secs = os.clock() - t0
    ha:write(("%d,%.4f,%s\n"):format(s, secs, a))
    hb:write(("%d,%.4f,%s\n"):format(s, secs, b)) end
  ha:close(); hb:close()
  return fa end

-- Return acc,pd,pf,d2h and auc,klasses of one forest over `te`.
-- `posts` is the vote share, so the label is its own argmax: the
-- two answers cannot disagree, as they could if each refit.
function hardBoth(tr,te,    i,col,bag,post,p,got,n,t,sum,k,a) --> str,str
  i, col, bag = forest(tr), tr.klass, Bag()
  post = {}
  for _, row in order(te.rows) do
    local tally, ks = i:votes(row)             -- `ks` is arrival order
    local z = 0
    for _, kk in order(ks) do z = z + tally[kk] end
    p, got, n = {}, nil, -1
    for _, kk in order(ks) do
      p[kk] = tally[kk] / max(z, 1)
      if tally[kk] > n then n, got = tally[kk], kk end end  -- ties: 1st
    post[row] = p
    bag:tally(row[col.at], got) end
  sum, k = 0, 0
  for x in pairs(col.has) do
    t = {}
    for _, row in order(te.rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    a = auc(t)
    if a then sum, k = sum + a, k + 1 end end
  return ("%.1f,%.1f,%.1f,%.3f"):format(bag:score()),
         ("%.4f,%d"):format(k > 0 and sum / k or 0, k) end

-- ---- one tree --------------------------------------------------------
-- `ens.py treedeep`: a single tree, every column, leaf 2, grown deep
-- enough to name every klass.  A tree of depth d holds at most
-- 2^(d-1) leaves, so a majority vote over 8 leaves cannot name 19
-- klasses -- it would report the shape of the tree, not what it
-- learned.  Take the smallest depth that can name them all, plus one
-- level of slack, and never less than 12.
function deepFor(tr,    ks,d) --> int
  ks, d = tr.klass:nVals(), 2
  while 2 ^ (d - 1) < ks do d = d + 1 end
  return max(the.depth, d + 1) end

-- The label is the leaf's `mu`, not an argmax over `posts`.  Both
-- read the same counts, but `mu` is `Sym.mid` -- keys sorted, strict
-- `>` -- while an argmax over `posts` walks `pairs`, whose order no
-- two ports share.  They differ only on a tie, and only one of them
-- differs the same way every time.
function treeBoth(tr,te,    i,col,bag,post,n,t,sum,k,a,was) --> str,str
  was = {the.depth, the.leaf}
  the.depth, the.leaf = deepFor(tr), 2
  i = Tree(tr, tr.rows, function(row) return row[tr.klass.at] end,
           Sym, 1, 0)                      -- `0`: every column
  the.depth, the.leaf = was[1], was[2]
  col, bag, post = tr.klass, Bag(), {}
  for _, row in order(te.rows) do
    post[row] = i:posts(row)
    bag:tally(row[col.at], i:pick(row).mid) end
  sum, k = 0, 0
  for x in pairs(col.has) do
    t = {}
    for _, row in order(te.rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    a = auc(t)
    if a then sum, k = sum + a, k + 1 end end
  return ("%.1f,%.1f,%.1f,%.3f"):format(bag:score()),
         ("%.4f,%d"):format(k > 0 and sum / k or 0, k) end

-- ---- rigs ------------------------------------------------------------
-- ARM names the pair of csvs written, so this rig can fill the
-- `hardeep` slot `ens.py` used to fill, or sit beside it under
-- another name while the two are compared.
slow.hard = function()
  print(scored2(the.file, os.getenv("ARM") or "hard", hardBoth)) end
slow.tree = function()
  print(scored2(the.file, os.getenv("ARM") or "tree", treeBoth)) end

if (arg and arg[0] or ""):find"forest%-eg%.lua$" then
  the = cli()
  ok, err = pcall(slow[the.go] or fast[the.go]
                  or function() error("no go=" .. tostring(the.go)) end)
  if not ok then
    io.stderr:write(the.file, ": ", tostring(err), "\n") end end
return _ENV
