#!/usr/bin/env luajit
-- vim: set ts=2 sw=2 sts=2 et cc=75 :
-- fft-eg.lua: one deep tree, fanned into fast-and-frugal trees; the
-- best of them picked on TRAIN, then applied to test.
--
-- An FFT is a chain: each test sends one side out to a leaf and
-- carries the other side on.  So one FFT is one root-to-leaf path of
-- the tree, with every off-path sibling collapsed to its majority.
-- Fan the whole tree and you get one FFT per leaf -- which at
-- `leaf=2` is thousands, and all of them long.  A long chain is not
-- frugal and its deepest exits hold four rows, so the fan is cut at
-- KMAX: stop there and let the node that remains answer with its own
-- `mid`.  Candidates are then every node at depth <= KMAX, each
-- offered once, so at most 2^(KMAX+1) of them.
--
-- This is a search for ONE tree, not an ensemble.  Nothing is
-- averaged.  The forest earns its keep by decorrelating members;
-- these candidates all come off a single fit and are maximally
-- correlated, so averaging them would mostly rebuild the tree they
-- came from.
--
-- Scoring a candidate costs no rows.  A row's answer depends only on
-- where its own path first leaves the spine, and every node already
-- carries the klass counts of the rows beneath it -- `all.has` from
-- growing the tree.  So walk the tree once, adding each sibling's
-- counts to a running confusion and undoing them on the way back,
-- and every candidate is scored for O(spine x klasses).
--
-- The counts shortcut is exact, not close.  BAG.tally only ever
-- increments n, ok, want, got and hit, so adding a count in one go
-- lands the same integers as calling it that many times, and
-- BAG.score reads only those finished counts, over klasses it sorts
-- itself.  Nothing here can move another arm's numbers: the library
-- is untouched, the shortcut runs on TRAIN only, and the score that
-- reaches the csv is a row-by-row BAG.tally like every other arm's.
--
-- TABDIR picks which `tab` answers the require, so the same rig can
-- score the yue build the other arms were scored with.
--   usage: TABDIR=... luajit etc/fft-eg.lua go=fft file=f.csv
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

Kmax = tonumber(os.getenv("KMAX")) or 8
reps = tonumber(os.getenv("REPS")) or reps

-- ---- the tree the fan comes off -------------------------------------
-- `forest-eg.lua`'s single-tree arm, verbatim: depth grows with the
-- klass count, because a tree of depth d holds at most 2^(d-1)
-- leaves and cannot name more klasses than it has leaves.
function deepFor(tr,    ks,d) --> int
  ks, d = tr.klass:nVals(), 2
  while 2 ^ (d - 1) < ks do d = d + 1 end
  return max(the.depth, d + 1) end

function deepTree(tr,    i,was) --> TREE
  was = {the.depth, the.leaf}
  the.depth, the.leaf = deepFor(tr), 2
  i = Tree(tr, tr.rows, function(row) return row[tr.klass.at] end,
           Sym, 1, 0)                      -- `0`: every column
  the.depth, the.leaf = was[1], was[2]
  return i end

-- ---- test counts, so the oracle costs one pass ----------------------
-- Leave every node a tally of the test klasses that reach it, the
-- same way `all.has` holds the train ones.  Then the spine
-- arithmetic below scores a candidate on test too, and the best FFT
-- the tree COULD give is known for the price of one descent.  That
-- number never picks anything -- it is there to measure how much
-- picking on train costs.
function teSeed(nd,rows,col,    a,b,c,t) --> nil
  nd.te = {}
  for _, row in order(rows) do
    t = row[col.at]; nd.te[t] = (nd.te[t] or 0) + 1 end
  if nd.at then
    a, b, c = {}, {}, nd.at
    for _, row in order(rows) do
      t = c.col:holds(row[c.col.at], c.v) and a or b
      t[#t + 1] = row end
    teSeed(nd.left, a, col)
    teSeed(nd.right, b, col) end end

-- ---- the running confusion ------------------------------------------
-- Count every row under `has` as a guess of `lab`; `sgn` -1 undoes
-- it on the way back up.  `pairs` is safe here and only here: these
-- are integers landing in slots of their own, so no two orders can
-- disagree.  Every float sum still happens inside BAG.score, over
-- klasses it sorts.
function bump(conf,has,lab,sgn,    t) --> nil
  if not has then return end
  for k, n in pairs(has) do
    t = conf[k]; if not t then t = {}; conf[k] = t end
    t[lab] = (t[lab] or 0) + sgn * n end end

-- A BAG holding exactly what `conf` says, so BAG.score does the
-- arithmetic and this arm's columns mean what every other arm's do.
function confBag(conf,    b) --> BAG
  b = Bag()
  for want, gots in pairs(conf) do
    for got, n in pairs(gots) do
      if n > 0 then
        b.n          = b.n + n
        b.want[want] = (b.want[want] or 0) + n
        b.got[got]   = (b.got[got]   or 0) + n
        if want == got then
          b.ok       = b.ok + n
          b.hit[got] = (b.hit[got] or 0) + n end end end end
  return b end

-- ---- the fan ---------------------------------------------------------
-- Offer the spine as it stands: `tail` answers everyone still in
-- play.  Train picks; test is recorded beside it, and separately the
-- best test score any candidate reached -- the oracle.
function offer(st,depth,tail,sp,    a,b,j) --> nil
  a = confBag(st.tr):score()
  b = confBag(st.te):score()
  if a > st.acc then
    st.acc, st.teAcc, st.k, st.tail, st.sp = a, b, depth, tail, {}
    for j = 1, depth do st.sp[j] = sp[j] end end
  if b > st.oracle then st.oracle, st.oracleK = b, depth end end

-- Walk the tree, offering a candidate at every node within KMAX.
-- Two moves at each node: stop, or spend one more test and send one
-- child out as a leaf.  The counts are added before the descent and
-- taken back after, so the confusion always says exactly what the
-- spine in hand would score.
function fan(nd,k,depth,st,sp,    out,rest) --> nil
  bump(st.tr, nd.all.has, nd.mid, 1)
  bump(st.te, nd.te,      nd.mid, 1)
  offer(st, depth, nd, sp)
  bump(st.tr, nd.all.has, nd.mid, -1)
  bump(st.te, nd.te,      nd.mid, -1)
  if nd.at and k > 0 then
    for _, yes in ipairs{false, true} do
      out  = yes and nd.left  or nd.right
      rest = yes and nd.right or nd.left
      sp[depth + 1] = {nd = nd, out = out}
      bump(st.tr, out.all.has, out.mid, 1)
      bump(st.te, out.te,      out.mid, 1)
      fan(rest, k - 1, depth + 1, st, sp)
      bump(st.tr, out.all.has, out.mid, -1)
      bump(st.te, out.te,      out.mid, -1) end end end

-- ---- predicting ------------------------------------------------------
-- The first test that sends `row` out is the one that answers it.
function fftGuess(st,row,    s,c) --> atom
  for j = 1, st.k do
    s = st.sp[j]; c = s.nd.at
    if (c.col:holds(row[c.col.at], c.v) and s.nd.left or s.nd.right)
       == s.out then return s.out.mid end end
  return st.tail.mid end

-- ---- scoring ---------------------------------------------------------
-- DIAG collects what the search did, for a report the csv has no
-- column for: which spine length won, and what the best spine in
-- this tree would have scored had test been allowed to pick it.
Diag = {}

function fftScore(tr,te,    i,st,bag,col) --> str
  i = deepTree(tr)
  teSeed(i, te.rows, tr.klass)
  st = {tr = {}, te = {}, acc = -1, oracle = -1, oracleK = 0}
  fan(i, Kmax, 0, st, {})
  bag, col = Bag(), tr.klass
  for _, row in order(te.rows) do
    bag:tally(row[col.at], fftGuess(st, row)) end
  Diag[#Diag + 1] = {k = st.k, tr = st.acc, te = st.teAcc,
                     oracle = st.oracle, oracleK = st.oracleK}
  return Acc:format(bag:score()) end

-- ---- rigs ------------------------------------------------------------
slow.fft = function(    f)
  f = scored(the.file, os.getenv("ARM") or "fft", fftScore, AccCols)
  if os.getenv("DIAG") then
    for s, d in ipairs(Diag) do
      io.stderr:write(("%s,%d,%d,%.1f,%.1f,%.1f,%d\n"):format(
        the.file:match"([^/]+)%.csv$", s, d.k, d.tr, d.te,
        d.oracle, d.oracleK)) end end
  print(f) end

-- The chosen FFT's posterior: the distribution of the exit `row`
-- falls out of, normalized.  A hard label has no ranking, so without
-- this the arm has no auc to report -- same reason `Hard.posts`
-- exists for the forest.
function fftPosts(st,row,    s,c,nd,t,z) --> dict
  nd = st.tail
  for j = 1, st.k do
    s = st.sp[j]; c = s.nd.at
    if (c.col:holds(row[c.col.at], c.v) and s.nd.left or s.nd.right)
       == s.out then nd = s.out; break end end
  t, z = {}, 0
  for _, n in pairs(nd.all.has) do z = z + n end
  for k, n in pairs(nd.all.has) do t[k] = n / max(z, 1) end
  return t end

function fftAuc(tr,te,    i,st,col,post,t,cols) --> str
  i = deepTree(tr)
  teSeed(i, te.rows, tr.klass)
  st = {tr = {}, te = {}, acc = -1, oracle = -1, oracleK = 0}
  fan(i, Kmax, 0, st, {})
  col, post = tr.klass, {}
  for _, row in order(te.rows) do post[row] = fftPosts(st, row) end
  cols = {}
  for _, x in order(keys(col.has)) do
    t = {}
    for _, row in order(te.rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    cols[#cols + 1] = t end
  return aucline(cols) end

slow.fftauc = function()
  print(scored(the.file, (os.getenv("ARM") or "fft") .. "auc",
               fftAuc, AucCols)) end

if (arg and arg[0] or ""):find"fft%-eg%.lua$" then
  the = cli()
  ok, err = pcall(slow[the.go] or fast[the.go]
                  or function() error("no go=" .. tostring(the.go)) end)
  if not ok then
    io.stderr:write(the.file, ": ", tostring(err), "\n") end end
return _ENV
