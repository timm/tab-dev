#!/usr/bin/env luajit
-- vim: set ts=2 sw=2 sts=2 et cc=75 :
-- rnb-eg.lua: a random forest's two tricks, on naive Bayes.
--
-- Row subsampling alone would buy nothing here.  Bagging kills
-- variance and naive Bayes has little -- thirty bootstraps of a
-- counter produce thirty near-identical counters.  The column
-- subspace is what earns the ensemble: NB's one real weakness is
-- that correlated columns get counted twice and over-sharpen the
-- posterior, and a member that holds only sqrt(#x) of them cannot
-- make that mistake as often.  Averaging over subspaces is a BIAS
-- fix, not a variance fix.
--
-- And a soft vote over members on different subspaces is strictly
-- more expressive than any single NB: a mixture of log-linear models
-- is not log-linear.  So this is not just NB with error bars -- it
-- can represent things NB cannot, which is the only way past the
-- ~80 ceiling `CLAUDE.md` records for one counter.
--
-- Nothing is fitted twice.  `Nb` is `subs[v]:add(row)`, pure
-- counting, so a member "fitted on a bootstrap" is just that
-- member's counts.  One pass over the rows hands each row to the
-- members that drew it, and a member's multiplicity comes from
-- Poisson(1) -- the limit of Binomial(N,1/N), so this IS the
-- bootstrap, not an approximation of it (Oza & Russell).  P(absent)
-- = 1/e = .368, which is where the familiar .632 comes from.
-- WEIGHT=bern swaps in Bernoulli(.632): multiplicity 0 or 1, a
-- different estimator (subagging), kept as a knob rather than
-- assumed equivalent.
--
-- COLS=gain is offered but is NOT the default, for two reasons.
-- `CLAUDE.md` has info-gain column WEIGHTING at -4 to -6 accuracy --
-- a different use, inside NB rather than across members, so not a
-- repeat, but close enough to be careful.  The sharper worry is that
-- favouring high-gain columns makes every member pick the same ones,
-- which correlates them and is exactly what an ensemble must not do.
-- Random forests draw uniformly for that reason.
--
--   usage: TABDIR=... ROUNDS=30 COLS=sqrt VOTE=soft \
--          luajit etc/rnb-eg.lua go=rnb file=f.csv
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

Rounds = tonumber(os.getenv("ROUNDS")) or 30
Cols   = os.getenv("COLS")   or "sqrt"  -- sqrt|all|gain|<frac>
Weight = os.getenv("WEIGHT") or "poisson" -- poisson | bern
Vote   = os.getenv("VOTE")   or "soft"    -- soft | hard
reps   = tonumber(os.getenv("REPS")) or reps

-- ---- randomness ------------------------------------------------------
-- `rint` is the only stream in play, so a run repeats exactly.
function rnd() return (rint(1000000) - 1) / 1000000 end --> num in [0,1)

-- Knuth, with lambda 1: multiply uniforms until the product drops
-- under 1/e, and count how many it took.
function poisson1(    l,k,p) --> int
  l, k, p = exp(-1), 0, 1
  repeat k, p = k + 1, p * rnd() until p <= l
  return k - 1 end

function draw() --> int; how many copies of this row this member gets
  if Weight == "bern" then return rnd() < 0.632 and 1 or 0 end
  return poisson1() end

-- ---- the column subspace --------------------------------------------
-- Entropy of the klass left after splitting on `col`, subtracted from
-- the entropy before it: how much knowing this column tells you.
-- The table is already binned, so every column is symbolic and a
-- "split" is just its values.
function gainOf(trb,col,    n,ks,vs,h,hv,e,tot) --> num
  n, ks, vs = #trb.rows, {}, {}
  for _, row in order(trb.rows) do
    local k, v = row[trb.klass.at], row[col.at]
    ks[k] = (ks[k] or 0) + 1
    if v ~= "?" then
      vs[v] = vs[v] or {n = 0}
      vs[v].n, vs[v][k] = vs[v].n + 1, (vs[v][k] or 0) + 1 end end
  e = function(t, m,    s)                 -- entropy of counts `t`
        s = 0
        for _, c in pairs(t) do
          if type(c) == "number" and c > 0 then
            s = s - (c/m) * log(c/m) / log(2) end end
        return s end
  h, hv, tot = e(ks, n), 0, 0
  for _, t in pairs(vs) do
    hv, tot = hv + (t.n/n) * e(t, t.n), tot + t.n end
  return max(0, h - hv) end

-- `n` columns for one member.  Uniform by default: a member that
-- always holds the best columns is the same member every time.
-- Returns POSITIONS in `x`, not columns.  `NB.like` reads
-- `col1.has[v]`, the count of `v` in THIS KLASS -- so a member's
-- columns must be re-read off each klass's own sub-TAB.  Handing it
-- the shared `trb.x` columns instead gives every klass the same
-- likelihood, and the vote collapses to a constant.
function pickCols(trb,gains,    xs,n,u,tot,r,acc) --> list of int
  xs = {}
  for j = 1, #trb.x do xs[#xs + 1] = j end
  if Cols == "all" or #xs <= 1 then return xs end
  -- A tree draws sqrt(#x) AT EVERY SPLIT, so a deep member still
  -- touches many columns.  An NB member sees only what it is given,
  -- once, for good -- so sqrt leaves it far blinder than the forest
  -- analogy suggests.  COLS may therefore be a fraction (0<f<1) or a
  -- count, not just the sqrt rule.
  n = tonumber(Cols)
  n = n and (n < 1 and max(1, floor(n * #xs)) or min(#xs, floor(n)))
        or max(1, floor(sqrt(#xs)))
  u = {}
  if Cols == "gain" then
    for _ = 1, n do                        -- roulette, no replacement
      tot = 0
      for _, c in order(xs) do tot = tot + (gains[c] or 0) end
      if tot <= 0 then break end
      r, acc = rnd() * tot, 0
      for k, c in order(xs) do
        acc = acc + (gains[c] or 0)
        if acc >= r then u[#u + 1] = c; table.remove(xs, k); break end end end
    if #u == 0 then u[1] = xs[1] end
  else
    shuffle(xs)
    for k = 1, n do u[k] = xs[k] end end
  return u end

-- ---- the members -----------------------------------------------------
-- One pass over the rows.  Each member collects the rows it drew,
-- with multiplicity, and only then counts them -- `Nb` is a counter,
-- so this is the same model a member fitted on its own bootstrap
-- would have been, reached without building that bootstrap.
function members(trb,    ms,gains,k,m) --> list
  gains = {}
  if Cols == "gain" then
    for j, c in order(trb.x) do gains[j] = gainOf(trb, c) end end
  ms = {}
  for j = 1, Rounds do ms[j] = {rows = {}, cols = pickCols(trb, gains)} end
  for _, row in order(trb.rows) do
    for j = 1, Rounds do
      k, m = draw(), ms[j].rows
      for _ = 1, k do m[#m + 1] = row end end end
  for j = 1, Rounds do
    if #ms[j].rows == 0 then ms[j].rows = trb.rows end  -- never empty
    ms[j].nb  = Nb(trb, ms[j].rows)
    ms[j].sub = {}                       -- this member's columns, as
    for _, k in order(ms[j].nb:klasses()) do   -- each klass holds them
      local t = {}
      for _, at in order(ms[j].cols) do t[#t + 1] = ms[j].nb.subs[k].x[at] end
      ms[j].sub[k] = t end end
  return ms end

-- ---- asking a member -------------------------------------------------
-- `NB.like`'s third argument is the whole point: one NB, asked about
-- just this member's columns.
function memGuess(m,row,    b,bk,v) --> atom
  b = -math.huge
  for _, k in order(m.nb:klasses()) do
    v = m.nb:like(m.nb.subs[k], row, m.sub[k])
    if v > b then b, bk = v, k end end     -- strict: first wins
  return bk end

function memPosts(m,row,    ks,t,hi,z,u) --> dict
  ks, t, hi = m.nb:klasses(), {}, -math.huge
  for _, k in order(ks) do
    t[k] = m.nb:like(m.nb.subs[k], row, m.sub[k])
    hi   = max(hi, t[k]) end
  z = 0
  for _, k in order(ks) do t[k] = exp(t[k] - hi); z = z + t[k] end
  u = {}
  for _, k in order(ks) do u[k] = t[k] / z end
  return u end

-- ---- the vote --------------------------------------------------------
-- Hard: one label per member.  Soft: the members' posteriors added,
-- which is the mixture that a single NB could not have written down.
function votes(ms,row,    t,got,n,p,g) --> atom, dict
  t = {}
  for _, m in order(ms) do
    if Vote == "hard" then
      g = memGuess(m, row)
      t[g] = (t[g] or 0) + 1
    else
      p = memPosts(m, row)
      for _, k in order(sortedKeys(p)) do
        t[k] = (t[k] or 0) + p[k] end end end
  n, got = -math.huge, nil
  for _, k in order(sortedKeys(t)) do
    if t[k] > n then n, got = t[k], k end end   -- strict: first wins
  return got, t end

function sortedKeys(t,    u) --> list; sorted, so a tie falls one way
  u = {}
  for k in pairs(t) do u[#u + 1] = k end
  sort(u, function(a, b) return tostring(a) < tostring(b) end)
  return u end

-- ---- scoring ---------------------------------------------------------
function rnbScore(tr,te,    trb,teb,ms,bag,col) --> str
  trb = tr:clone(tr.rows, "bin")
  teb = tr:clone(te.rows, "bin")
  ms  = members(trb)
  bag, col = Bag(), trb.klass
  for _, row in order(teb.rows) do
    bag:tally(row[col.at], (votes(ms, row))) end
  return Acc:format(bag:score()) end

function rnbAuc(tr,te,    trb,teb,ms,col,post,t,cols,ks) --> str
  trb = tr:clone(tr.rows, "bin")
  teb = tr:clone(te.rows, "bin")
  ms, col, post = members(trb), trb.klass, {}
  for _, row in order(teb.rows) do
    local _, p = votes(ms, row)
    post[row] = p end
  ks = {}
  for _, x in order(keys(col.has)) do ks[#ks + 1] = x end
  cols = {}
  for _, x in order(ks) do
    t = {}
    for _, row in order(teb.rows) do
      t[#t + 1] = {post[row][x] or 0, row[col.at] == x} end
    cols[#cols + 1] = t end
  return aucline(cols) end

-- ---- rigs ------------------------------------------------------------
slow.rnb = function()
  print(scored(the.file, os.getenv("ARM") or "rnb", rnbScore, AccCols)) end
slow.rnbauc = function()
  print(scored(the.file, (os.getenv("ARM") or "rnb") .. "auc",
               rnbAuc, AucCols)) end

if (arg and arg[0] or ""):find"rnb%-eg%.lua$" then
  the = cli()
  ok, err = pcall(slow[the.go] or fast[the.go]
                  or function() error("no go=" .. tostring(the.go)) end)
  if not ok then
    io.stderr:write(the.file, ": ", tostring(err), "\n") end end
return _ENV
