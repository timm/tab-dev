#!/usr/bin/env python3
# vim: set ts=2 sw=2 sts=2 et cc=75 :
"""tabfast.py: RETIRED -- the OPTIMIZED histogram cut, in python.

Kept for one reason: this is the only python that matched `tab.lua`
40/40 on moot/classify, on the root cut AND the whole tree shape
(column, threshold, node count, leaf count, root majority).  The live
file, `~/gh/tab/tab3.py`, carries the unoptimized cut instead and
already differs from lua on tree shape, so if a rebuilt fast cut has
to be checked against something, it is this.

What makes it fast, and what `tab3.py` deliberately has none of:
  * a flat `Hist[bin*nk + klass]` count array, with `ThisC`/`ThatC`
    scratch hoisted to module level and reused
  * `binRows`: a bin id cached per (row, column) past the end of the
    row, plus klass strings coded to small ints, once per table
  * `Sym.vs`/`Sym.vi`, so a symbolic value indexes that flat array
  * `cl` carried incrementally through the numeric sweep

Superseded 2026-11-13.  Do not edit; rebuild from `tab3.py` under the
profiler instead.
"""
import sys, os, re, math
from functools import cached_property
from math import exp, log, log2, sqrt, floor

class o: # A bag of named slots, printed as its own fields."
  def __init__(i, **d): i.__dict__.update(d)
  def __repr__(i): return say(i.__dict__)

the = o(version="0.6.0", bins=7, budget=50, check=5, fmt="%.2f",
        cuts=50, depth=12, few=128, first=4, leaf=2, m=2, p=2,
        reps=3, rounds=30, seed=1234567891, file=None,
        train="~/gits/moot/optimize/misc/auto93.csv")

# ---- values ----------------------------------------------------------
def value(s): # int float or string
  s = s.strip()
  try: return int(s)
  except ValueError:
    try: return float(s)
    except ValueError: return s

def values(s): return [value(x) for x in s.split(",")]

def csv(file):  # rows of `file`; skip blank and commented liens
  with open(os.path.expanduser(file)) as f:
    return [values(s) for line in f
            if (s := line.strip()) and not s.startswith("#")]

# ---- columns ---------------------------------------------------------
def Col(txt, at): return (Num if txt[:1].isupper() else Sym)(txt, at)

class Sym:  # a count per value; `div` is their entropy.
  def __init__(i, txt="S", at=0):
    i.txt, i.at, i.n, i.has, i.kinds = txt, at, 0, {}, None

  def add(i, v, inc=1):
    # `inc=-1` takes one back out.  ONE caller: `Tab.sub`, i.e. the
    # row `acquire` demotes from `best` to `rest`.  The cut in this
    # file counts into `Hist` and never moves a column's counts --
    # the UNOPTIMIZED cut does, which is where this started.
    if v != "?":
      i.n += inc
      c = i.has.get(v, 0) + inc
      if c > 0: i.has[v] = c
      else: i.has.pop(v, None)         # a count of 0 is not a value
    return v

  def mid(i): return max(i.has, key=i.has.get, default=None)

  def div(i):
    "Shannon entropy, in bits."
    return 0 if i.n < 1 else -sum((c / i.n) * log2(c / i.n)
                                  for c in i.has.values())
  ops = ("==", "!=")            # how a cut of it reads
  def norm(i, v)     : return v
  def holds(i, x, v) : return x == "?" or x == v
  def bin(i, v)      : return v
  def nVals(i)       : return max(2, len(i.has))

  # A Sym's bins are its own values, numbered once.  Same contract as
  # `Num.half`/`Num.r`: fixed at first use, shared by every tree.
  @cached_property
  def vs(i): return sorted(i.has, key=str)      # bin -> value

  @cached_property
  def vi(i): return {v: n for n, v in enumerate(i.vs)}   # value -> bin

  def slots(i): return len(i.vi)
  def edge(i, b): return i.vs[b]
  def slot(i, x): return i.vi.get(x) if x != "?" else None

class Num:
  "Welford: a running mean and sd, with `add` reversible."
  ops = ("<=", ">")             # how a cut of it reads
  def __init__(i, txt="N", at=0):
    i.txt, i.at, i.n, i.mu, i.m2 = txt, at, 0, 0.0, 0.0
    i.w = 0 if txt.endswith("-") else 1

  def add(i, v, inc=1):
    # `inc=-1`: see `Sym.add`.  Only `acquire` reaches it, through
    # `Tab.sub`; Welford reverses, hence the `n <= 0` reset.
    if v != "?":
      i.n += inc
      if i.n <= 0: i.n, i.mu, i.m2 = 0, 0.0, 0.0
      else:
        d = v - i.mu
        i.mu += inc * d / i.n
        i.m2 += inc * d * (v - i.mu)
    return v

  def div(i): return 0 if i.n < 2 else sqrt(max(i.m2, 0) / (i.n - 1))
  def mid(i): return i.mu
  def holds(i, x, v): return x == "?" or x <= v   # "?" says yes, so a
                                                  # cut never loses a row
  def norm(i, v):
    "A logistic cdf, clipped at three standard deviations."
    if v == "?": return v
    z = (v - i.mu) / (i.div() + 1e-32)
    z = 3 if z > 3 else (-3 if z < -3 else z)
    return 1 / (1 + exp(-1.7 * z))

  def bin(i, v):
    "`min` is defence: `norm` tops out at .9939, but clamp anyway."
    if v == "?": return v
    return min(the.bins, 1 + floor(the.bins * i.norm(v)))

  # ---- binning ----
  # Computed on first use, then a plain instance attribute -- so `slot`
  # pays no call at all after the first row.  Both are READ-ONLY state:
  # `r` is set from `div()`, so a column that keeps growing after it has
  # binned keeps the width it first chose.  That is deliberate (every
  # tree and node must agree on the bins); `del col.r` re-derives.
  @cached_property
  def half(i): return floor(the.cuts / 2)   # bins each SIDE of the mean

  @cached_property
  def r(i): return 3 * i.div() / i.half     # so `half` bins reach 3sd

  # `2*half+1`, never `the.cuts`: a SECOND derivation of a number `slot`
  # has already pinned can disagree with it.  Change `the.cuts` after a
  # column has binned and `slots` would say 11 while `slot` still
  # returned up to 51 -- `tally` clears 1..11, bins 12..51 keep the
  # previous node's counts, and the wrong split is invisible.
  def slots(i): return 2 * i.half + 1
  def edge(i, b): return i.mu + (b - i.half - 0.5) * i.r
  def slot(i, x):
    if x == "?" or i.r <= 0: return None
    b = floor((x - i.mu) / i.r + 0.5)   # outliers pin to the end bins
    return min(i.half, max(-i.half, b)) + i.half

# ---- tables ----------------------------------------------------------
class Tab:
  "Rows, summarized in columns: x independents, y goals, maybe a klass."
  def __init__(i, src=None):
    i.rows, i.names, i.cols, i.x, i.y = [], [], [], [], []
    i.klass = i.binned = i.kodeAt = None
    i.nk = 0
    if src is not None:
      for row in (csv(src) if isinstance(src, str) else src): i.add(row)

  def add(i, row):
    "The first row is the column names."
    if not i.cols: return i.head(row)
    i.rows.append(row)
    for col in i.cols: col.add(row[col.at])
    return row

  def sub(i, row):
    """`add`'s inverse on the SUMMARIES only; `rows` is the caller's.

    Two jobs, two methods: `acquire` pops the row it is demoting off a
    sorted list -- which is where it knows the row is -- and then asks
    the columns to forget it.
    """
    for col in i.cols: col.add(row[col.at], -1)
    return row

  def head(i, names):
    "X skips, -+! are goals, ! is the klass, - means minimize."
    i.names = names
    for at, txt in enumerate(names):
      col = Col(txt, at)
      i.cols.append(col)
      if not txt.endswith("X"):
        if txt[-1] in "-+!":
          i.y.append(col)
          if txt.endswith("!"): i.klass = col
        else:
          i.x.append(col)

  def clone(i, rows=(), how=None):
    "A fresh Tab; `how='bin'` discretizes, so every column reads as Sym."
    head = [c.txt.lower() for c in i.cols] if how else i.names
    out = [head]
    for row in rows:
      out.append(row if not how else
                 [getattr(c, how)(row[c.at]) for c in i.cols])
    return Tab(out)

  def mid(i, cols=None):
    return {c.txt: c.mid() for c in (i.cols if cols is None else cols)}

  def mids(i):
    "`mid` keys on txt for printing; `xdist` reads a row, so: on `at`."
    return {c.at: c.mid() for c in i.cols}

  def ydist(i, row):
    """Distance to heaven.  An unknown goal reads as that column's middle
    -- three moot/regression sets carry a '?' in y, and without this the
    subtraction below dies on the string."""
    def on(col):
      v = row[col.at]
      if v == "?": v = col.mid()
      return abs(col.norm(v) - col.w) ** the.p
    return (sum(on(c) for c in i.y) / len(i.y)) ** (1 / the.p)

  def xdist(i, r1, r2):
    """Minkowski over x, each column normalised first.  An unknown is
    pushed to whichever end is FURTHER from what it meets, so saying
    nothing never reads as agreement."""
    def on(col):
      a, b = r1[col.at], r2[col.at]
      if a == "?" and b == "?": return 1
      if isinstance(col, Sym): return 0 if a == b else 1
      a, b = col.norm(a), col.norm(b)
      if a == "?": a = 0 if b > .5 else 1
      if b == "?": b = 0 if a > .5 else 1
      return abs(a - b) ** the.p
    return (sum(on(c) for c in i.x) / len(i.x)) ** (1 / the.p)

  def split(i):
    "80:20, off a copy -- never `i.rows` itself."
    rows = shuffle(list(i.rows))
    n = floor(.8 * len(rows))
    return rows[:n], rows[n:]

  def rank(i, rows, best, rest):
    """Order unseen rows by what `acquire` learnt: near `best`'s middle,
    far from `rest`'s.  BETTER FIRST -- the negation of the key
    `acquire` sorts on, which wants its pick at the END."""
    bmid, rmid = best.mids(), rest.mids()
    return sortBy(rows, lambda z: i.xdist(z, bmid) - i.xdist(z, rmid))

  def cut(i, rows, cols=0):
    """The cut of `rows` leaving the least klass entropy, found by
    counting.  Trees here grow over a KLASS only, so every target is a
    Sym and both column kinds reduce to one histogram: bin the column,
    count (bin x klass), sweep the boundaries.  Nothing is sorted.
    """
    box = o(s=None, col=None, v=None)
    def offer(score, v, col):
      if box.s is None or score < box.s:   # strict `<` keeps the FIRST
        box.s, box.col, box.v = score, col, v   # of a tie
    binRows(i)          # bins and klass codes: once a run, not a node
    for col in pick(i.x, cols):
      hist(col, rows, i.kodeAt, i.nk, offer)
    return o(col=box.col, v=box.v) if box.s is not None else None

# ---- the histogram cut -----------------------------------------------
# The same binned search as tab.yue:253-443, counted instead of
# accumulated.  The search this replaced built a Sym for each side of a
# cut and walked every row through both, spending a `log` per row per
# column per node; the profile put 53% of a run in there.
#
# Counting instead: one integer per (bin, klass).  Klass strings are
# coded to ints ONCE per table, so the inner loop never hashes; entropy
# is computed at the bin boundaries only.
#
# ThisC/ThatC/Hist are scratch, hoisted out of the search and reused, so
# a node pays for them once a run instead of once a column.  They hold
# no answers and each is cleared by its own writer.  The price: the
# search must not reenter itself.  `Tree.grow` obeys that -- it takes
# its cut, THEN recurses -- and a threaded forest would not.
ThisC, ThatC, Hist = [], [], []

def clog(c): return c * log(c) if c > 0 else 0.0

def ent(n, cl):
  "Entropy of `n` rows whose sum c*log c is `cl`, in NATS."
  return max(0.0, log(n) - cl / n)

def sc(nn, tcl, on, ocl):
  "Two sides, weighed by size.  The /log 2 comes out once, here."
  return (ent(nn, tcl) * nn + ent(on, ocl) * on) / (log(2) * (nn + on))

def binRows(tbl):
  """Bin every x value once and keep the id past the end of the row.

  A bin id is a function of (row, column) alone -- it does not depend on
  which rows a node holds -- and a Forest hands all its trees the same
  tbl and the same row objects.  Without this, one id is recomputed 34
  to 71 times a build.

  Writing into the row is safe because nothing reads a row's length, and
  `clone` builds a fresh Tab so `binAt` belongs to this table.  The ROWS
  though are shared with wherever they came from, so two tables binning
  the same rows would collide -- hence one entry point (`Tab.cut`) and
  the `binned` guard.  The klass rides along in the same place and for
  the same reason: the search wants it as a small int.
  """
  if tbl.binned: return
  tbl.binned = True
  off = len(tbl.cols)
  wide = off + len(tbl.cols)
  for row in tbl.rows:
    if len(row) < wide: row.extend([None] * (wide - len(row)))
  for col in tbl.x:
    col.binAt = off + col.at
    for row in tbl.rows: row[col.binAt] = col.slot(row[col.at])
  tbl.kodeAt, tbl.nk, seen = off + tbl.klass.at, 0, {}
  for row in tbl.rows:
    v = row[tbl.klass.at]
    if v not in seen:
      seen[v] = tbl.nk
      tbl.nk += 1
    row[tbl.kodeAt] = seen[v]

def tally(col, rows, kat, nk, nb):
  "Count rows into (bin x klass); report the occupied span and the n."
  need = nb * nk
  if len(Hist) < need: Hist.extend([0] * (need - len(Hist)))
  for k in range(need): Hist[k] = 0
  lo, up, nn, at = nb, -1, 0, col.binAt
  for row in rows:
    b = row[at]
    if b is not None:
      Hist[b * nk + row[kat]] += 1
      if b < lo: lo = b
      if b > up: up = b
      nn += 1
  return lo, up, nn

def numSweep(col, nk, lo, up, nn, out):
  """NUMERIC: walk left to right, moving each bin from `that` to `this`.

  `cl` is carried rather than rebuilt -- old term off, then new term on,
  in that order, because float addition is not associative and
  (cl-a)+z differs from cl+(z-a) by enough to flip a near-tie.
  """
  while len(ThisC) < nk: ThisC.append(0); ThatC.append(0)
  on, nn, tcl, ocl = nn, 0, 0.0, 0.0
  for i in range(nk):                   # `that` holds every row at first
    ThisC[i] = 0
    t = 0
    for b in range(lo, up + 1): t += Hist[b * nk + i]
    ThatC[i] = t
    ocl += clog(t)
  for b in range(lo, up):               # a cut after the last bin would
    base = b * nk                       # leave `that` empty
    for i in range(nk):
      c = Hist[base + i]
      if c == 0: continue
      a, z = clog(ThisC[i]), clog(ThisC[i] + c)
      ThisC[i], tcl = ThisC[i] + c, tcl - a + z
      a, z = clog(ThatC[i]), clog(ThatC[i] - c)
      ThatC[i], ocl = ThatC[i] - c, ocl - a + z
      nn, on = nn + c, on - c
    if nn < the.leaf or on < the.leaf: continue
    out(sc(nn, tcl, on, ocl), col.edge(b), col)

def symSweep(col, nk, lo, up, nn, out):
  """SYMBOLIC: a cut is `x == v`, so `this` is ONE bin on its own and
  `that` is everything else -- no carrying, and the bins need no order
  between them."""
  while len(ThatC) < nk: ThisC.append(0); ThatC.append(0)
  for i in range(nk):
    t = 0
    for b in range(lo, up + 1): t += Hist[b * nk + i]
    ThatC[i] = t
  for b in range(lo, up + 1):
    base, tn, on, tcl, ocl = b * nk, 0, 0, 0.0, 0.0
    for i in range(nk):
      c = Hist[base + i]
      d = ThatC[i] - c
      tn, tcl = tn + c, tcl + clog(c)
      on, ocl = on + d, ocl + clog(d)
    if tn < the.leaf or on < the.leaf: continue
    out(sc(tn, tcl, on, ocl), col.edge(b), col)

def hist(col, rows, kat, nk, out):
  """One column, counted and swept.  The only thing the two kinds still
  disagree about is what a cut MEANS, so that is the one thing asked of
  the column."""
  nb = col.slots()
  if not nb or nb <= 1: return
  lo, up, nn = tally(col, rows, kat, nk, nb)
  if nn < 2 * the.leaf or lo >= up: return
  sweep = symSweep if isinstance(col, Sym) else numSweep
  sweep(col, nk, lo, up, nn, out)

# ---- bayes -----------------------------------------------------------
class Nb:
  "One sub-Tab per klass in `rows`."
  def __init__(i, tbl, rows):
    i.tbl, i.subs, i.n, i.nKlass = tbl, {}, len(rows), 0
    for row in rows:
      v = row[tbl.klass.at]
      if v not in i.subs:
        i.subs[v], i.nKlass = tbl.clone(), i.nKlass + 1
      i.subs[v].add(row)

  def like(i, sub, row, cols=None):
    """log P(row | sub).  `cols` lets an ensemble member ask this one Nb
    about just its own subspace, with no second Nb built for it."""
    def on(col1):
      col, v = i.tbl.cols[col1.at], row[col1.at]
      if v == "?": return 0
      seen = col1.has.get(v, 0) + the.m
      return log(seen / (col1.n + the.m * col.nVals()))
    prior = log((len(sub.rows) + the.m) / (i.n + the.m * i.nKlass))
    return prior + sum(on(c) for c in (sub.x if cols is None else cols))

  def klasses(i):
    "Sorted, so a tie goes the same way in every port."
    return sorted(i.subs, key=str)

  def guess(i, row):
    b, bk = -math.inf, None
    for k in i.klasses():
      v = i.like(i.subs[k], row)
      if v > b: b, bk = v, k      # strict `>`: the first one wins
    return bk

  def posts(i, row):
    """p(klass | row).  `like` is a LOG likelihood, so the top one comes
    off before `exp`, which would otherwise underflow for every klass at
    once."""
    ks = i.klasses()
    t = {k: i.like(i.subs[k], row) for k in ks}
    hi = max(t.values())
    t = {k: exp(t[k] - hi) for k in ks}
    z = sum(t.values())
    return {k: t[k] / z for k in ks}

# ---- tree ------------------------------------------------------------
class Tree:
  """One node over `rows`, summarized then grown.

  `cols` is how many x columns a split may look at (0 = all); it rides
  down the tree so every node redraws its own few.  Trees here grow over
  a KLASS only -- a tree whose target is a distance has no entropy to
  count.
  """
  def __init__(i, tbl, rows=None, lvl=1, cols=0):
    i.tbl = tbl
    i.rows = tbl.rows if rows is None else rows
    i.lvl, i.cols, i.n, i.txt = lvl, cols, len(i.rows), ""
    i.at = i.left = i.right = i.subbed = i.model = None
    i.sum()
    i.grow()

  def sum(i):
    "What this node answers with: its klasses, and their majority."
    i.all = Sym()
    at = i.tbl.klass.at
    for row in i.rows: i.all.add(row[at])
    i.mid = i.all.mid()
    return i

  def grow(i):
    "Two kids, when a cut pays: deep enough, big enough, both sides kept."
    cut = (i.tbl.cut(i.rows, i.cols)
           if i.n >= 2 * the.leaf and i.lvl < the.depth else None)
    if cut:
      a, b = [], []
      for row in i.rows:
        (a if cut.col.holds(row[cut.col.at], cut.v) else b).append(row)
      if len(a) >= the.leaf and len(b) >= the.leaf:   # else, a bad cut
        i.at = cut
        i.left = Tree(i.tbl, a, i.lvl + 1, i.cols)
        i.right = Tree(i.tbl, b, i.lvl + 1, i.cols)
        yes, no = cut.col.ops   # the column says what its cut MEANS
        i.left.txt = f"{cut.col.txt} {yes} {show(cut.v)}"
        i.right.txt = f"{cut.col.txt} {no} {show(cut.v)}"
    return i

  def sub(i):
    """A Tab of just `i.rows`.  Cloning is the costliest thing a node can
    do and only REPORTING needs it, so it waits until asked.  A 30-tree
    forest never asks."""
    if i.subbed is None: i.subbed = i.tbl.clone(i.rows)
    return i.subbed

  def pick(i, row):
    "The leaf `row` falls into."
    if not i.at: return i
    c = i.at
    kid = i.left if c.col.holds(row[c.col.at], c.v) else i.right
    return kid.pick(row)

  def walk(i):
    todo = [i]
    while todo:
      n = todo.pop()
      if n.at: todo += [n.right, n.left]
      yield n

  def nb(i):
    "The leaf's own naive Bayes, fitted the first time asked for."
    if i.model is None: i.model = Nb(i.sub(), i.rows)
    return i.model

  def posts(i, row):
    "p(klass | row), off the leaf's own klass counts."
    n = i.pick(row)
    return {k: m / n.all.n for k, m in n.all.has.items()}

  def dict(i):
    t = {"n": i.n, "mid": i.mid}
    if i.txt: t["txt"] = i.txt
    for col in i.sub().y:
      t[col.txt] = col.mu if isinstance(col, Num) else col.mid()
    if i.at: t["left"], t["right"] = i.left.dict(), i.right.dict()
    return t

  def show(i):
    for n in i.walk():
      print("|  " * max(0, n.lvl - 2) + n.txt, n.n, show(n.mid), sep="\t")

# ---- forest ----------------------------------------------------------
class Forest:
  """`rounds` deep trees, each on its own bootstrap, each node splitting
  on sqrt(#x) columns it draws itself.  Breiman: rows sampled once per
  tree, attributes resampled at every split."""
  def __init__(i, tbl, rows=None, rounds=None):
    rows = tbl.rows if rows is None else rows
    c = max(1, floor(sqrt(len(tbl.x))))
    i.tbl = tbl
    i.all = [Tree(tbl, some(rows, len(rows)), 1, c)
             for _ in range(rounds or the.rounds)]

  def votes(i, row):
    """A HARD vote.  `ks` is the order labels first arrived in, and that
    order is the tie-break -- two labels on 15 votes each are settled by
    which tree spoke first, which is the same in any port."""
    t, ks = {}, []
    for m in i.all:
      k = m.pick(row).mid
      if k is not None:
        if k not in t: ks.append(k)
        t[k] = t.get(k, 0) + 1
    return t, ks

  def posts(i, row):
    "The tally, normalized, so an auc still has a score to rank by."
    t, ks = i.votes(row)
    z = max(sum(t[k] for k in ks), 1)
    return {k: t[k] / z for k in ks}

  def guess(i, row):
    t, ks = i.votes(row)
    b, bk = -1, None
    for k in ks:
      if t[k] > b: b, bk = t[k], k    # strict: first wins
    return bk

# ---- acquire ---------------------------------------------------------
def acquire(tab, cap=None, y=None):
  """Spend the label budget on rows worth labelling.

  `the.first` rows are labelled blind; the best few become `best`, the
  others `rest`.  After that every pick is the unlabelled row furthest
  from `rest`'s middle and nearest `best`'s.

  `y` scores a row, LOWER being better, and defaults to distance to
  heaven.  A caller scored on something else must say so, or acquire
  hunts one end of the data while its judge rewards the other.
  """
  cap = the.budget - the.check if cap is None else cap
  y = y or (lambda r: tab.ydist(r))
  pool = shuffle(list(tab.rows))        # a copy, never `tab.rows`
  todo = pool[:min(the.few, len(pool))]
  both = tab.clone()
  for _ in range(min(the.first, len(todo))): both.add(todo.pop())
  sortBy(both.rows, y)
  k = floor(the.first ** .5)
  best, rest = tab.clone(), tab.clone()
  for j, row in enumerate(both.rows):
    (best if j < k else rest).add(row)
  while todo and len(both.rows) < cap:
    bmid, rmid = best.mids(), rest.mids()
    # ASCENDING, so the best bet is the LAST item and the next pick is
    # a pop off the end.
    sortBy(todo, lambda z: tab.xdist(z, rmid) - tab.xdist(z, bmid))
    best.add(both.add(todo.pop()))
    sortBy(best.rows, y)
    # `best` holds the top sqrt(n) by ydist, just sorted ascending, so
    # the LAST row is the worst in it: pop that (O(1) at the end), tell
    # `best`'s columns to forget it, and hand it to `rest`.
    if len(best.rows) > len(both.rows) ** .5:
      rest.add(best.sub(best.rows.pop()))
  return both.rows, best, rest

# ---- misc ------------------------------------------------------------
_rng = None

def seed(n=None):
  """Restart the generator.  The SETTING and the STATE are two things:
  `the.seed` says where a run began, `_rng` is where it has got to."""
  global _rng
  _rng = the.seed if n is None else n

def rint(n):
  "An int in 1..n, repeatable from the seed.  A 16807 Lehmer, as in lua."
  global _rng
  _rng = (16807 * (the.seed if _rng is None else _rng)) % 2147483647
  return 1 + floor(n * _rng / 2147483647)

def shuffle(t):
  "`t`, Fisher-Yates shuffled in place."
  for k in range(len(t), 1, -1):
    j = rint(k)
    t[k - 1], t[j - 1] = t[j - 1], t[k - 1]
  return t

def some(t, n=None):
  """`n` of `t`, drawn WITH replacement: one bootstrap.  At n=len(t) about
  63% of `t` turns up at least once, so the rest is that member's
  out-of-bag rows -- free held-out data, no extra split."""
  return [t[rint(len(t)) - 1] for _ in range(len(t) if n is None else n)]

def pick(t, n):
  """`n` of `t`, no replacement; all of `t` when `n` is 0 or too big.
  A forest redraws its columns at EVERY node, so the draw order matters:
  shuffle the whole list, then truncate, exactly as lua does, or `rint`
  is called a different number of times and the trees come out different.
  """
  if not n or n == 0 or n >= len(t): return t
  return shuffle(list(t))[:n]

def adds(src, it=None, on=None):
  it = Num() if it is None else it
  for x in src: it.add(x if on is None else on(x))
  return it

def sortBy(u, on):
  """`u` sorted in place by `on(v)`, ties left where they arrived.
  Python's sort is stable, which is exactly the tie-break lua has to
  build by hand."""
  u.sort(key=on)
  return u

def show(x):
  "A fraction through `the.fmt`; everything else as itself."
  if isinstance(x, float) and x != floor(x): return the.fmt % x
  return str(x)

def say(d, indent=0):
  "`d` as 'k=v k=v' lines, keys sorted; a nested dict goes one stop in."
  pad, flat, out = "  " * indent, [], []
  for k in sorted(d, key=str):
    if not isinstance(d[k], dict): flat.append(f"{k}={show(d[k])}")
  if flat: out.append(pad + " ".join(flat))
  for k in sorted(d, key=str):
    if isinstance(d[k], dict):
      out.append(pad + str(k))
      out.append(say(d[k], indent + 1))
  return "\n".join(out)

# ---- tests -----------------------------------------------------------
# Demos double as tests, and every golden number below is tab.yue's own.
eg = {}

def near(a, b): return abs(a - b) < 1e-6

def ok(got, want):
  assert got == want or (isinstance(got, (int, float)) and
                         isinstance(want, (int, float)) and
                         near(got, want)), f"{got} ~= {want}"
  return got

def test(f): eg["--" + f.__name__] = f; return f

@test
def values_(): 
  t = values(" 4.2, x,3")
  print(say({"got": str(t)}))
  ok(t[0], 4.2); ok(t[1], "x"); ok(t[2], 3)

@test
def csv_():
  t = csv(the.train)
  print(say({"rows": len(t), "cells": len(t[0])}))
  ok(len(t), 399); ok(len(t[0]), 8); ok(t[0][0], "Clndrs")

@test
def num():
  n = adds([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  print(say({"mu": n.mid(), "sd": n.div()}))
  ok(n.div(), 3.0276503541)

@test
def sym():
  s = adds(["a", "a", "b", "c", "c", "c"], Sym())
  print(say({"mode": s.mid(), "ent": s.div()}))
  ok(s.div(), 1.4591479170)

@test
def tab():
  t = Tab(the.train)
  print(say({"rows": len(t.rows), "x": len(t.x), "y": len(t.y)}))
  ok(len(t.rows), 398); ok(len(t.x), 4); ok(len(t.y), 3)

@test
def mid():
  t = Tab(the.train)
  print(say(t.mid(t.y)))
  ok(t.mid(t.y)["Acc+"], 15.5680904523)

@test
def ydist():
  t = Tab(the.train)
  print(say({"guzzler": t.ydist(t.rows[0]),
             "honda": t.ydist(t.rows[397])}))
  ok(t.ydist(t.rows[0]), 0.7863215821)
  ok(t.ydist(t.rows[397]), 0.1410148526)

@test
def split():
  t = Tab(the.train)
  tr, te = t.split()
  print(say({"train": len(tr), "test": len(te)}))
  ok(len(tr), 318); ok(len(te), 80)
  ok(",".join(str(v) for v in tr[0]), "6,145,76,81,2,3160,19.6,30")
  ok(t.rows[0][0], 8)             # t.rows itself was not disturbed

@test
def nb():
  t = Tab([["Age", "job", "klass!"],
           [20, "low", "no"], [22, "low", "no"], [25, "low", "no"],
           [30, "med", "no"], [60, "hi", "yes"], [62, "hi", "yes"],
           [65, "med", "yes"], [70, "hi", "yes"]])
  b = t.clone(t.rows, "bin")
  i = Nb(b, b.rows)
  print(say({"young": i.guess(b.rows[0]), "old": i.guess(b.rows[7])}))
  ok(i.guess(b.rows[0]), "no"); ok(i.guess(b.rows[7]), "yes")

@test
def acq():
  "Where a budget of labels landed."
  tb = Tab(the.train)
  def mu(rows):
    u = sorted(tb.ydist(r) for r in rows)
    return u[0], sum(u) / len(u)
  tr, te = tb.split()             # acquire on the 80, rank the 20 it
  got, best, rest = acquire(tb.clone(tr))        # has never been shown
  held = tb.rank(list(te), best, rest)
  top = held[:min(the.check, len(held))]
  print(say({"n": len(got), "acqBest": mu(got)[0], "acqMu": mu(got)[1],
             "top5": mu(top)[0], "heldBest": mu(te)[0],
             "heldMu": mu(te)[1]}))
  ok(mu(top)[0], 0.1569024159)

@test
def tree():
  "A deep tree, and a 30-tree forest, over a binned klass."
  tb = Tab(the.train)
  b = tb.clone(tb.rows, "bin")
  b.klass = b.y[-1]
  t = Tree(b, b.rows)
  print(say({"leaves": sum(1 for n in t.walk() if not n.at),
             "root": t.mid, "guess1": str(t.pick(b.rows[0]).mid)}))
  f = Forest(b, b.rows, 5)
  print(say({"trees": len(f.all), "vote1": str(f.guess(b.rows[0]))}))
  ok(len(f.all), 5)

@test
def say_():
  s = say({"seed": 1, "go": "nb", "sub": {"b": 2, "a": 1}})
  print(s)
  ok(s, "go=nb seed=1\nsub\n  a=1 b=2")

@test
def data():
  """Read `the.file` (or `the.train`) and say what came back.

  The other read tests assert auto93's own numbers, so they only pass on
  auto93.  This one asserts nothing about the CONTENT -- it checks the
  three things that are wrong when a read is broken, on ANY csv: every
  row is as wide as the header, every x and y column is the kind its
  name asked for, and no column is all "?" .  Then it prints the header
  so the eye can check the rest.
  """
  f = the.file or the.train
  # The raw rows FIRST.  `Tab.add` indexes `row[col.at]`, so a short
  # line raises IndexError there and a check made after the build can
  # never see one -- it is the csv that has to be measured, not the Tab.
  raw = csv(f)
  w = len(raw[0])
  bad = [j + 1 for j, r in enumerate(raw) if len(r) != w]
  if bad:
    print(say({"file": os.path.basename(f), "header": w,
               "RAGGED": str(bad[:10]), "of": len(bad)}))
    ok(bad, [])
  t = Tab(f)
  print(say({"file": os.path.basename(f), "rows": len(t.rows),
             "cols": w, "x": len(t.x), "y": len(t.y),
             "klass": str(t.klass and t.klass.txt)}))
  for col in t.cols:
    kind = "Num" if isinstance(col, Num) else "Sym"
    role = ("klass" if col is t.klass else
            "y" if col in t.y else "x" if col in t.x else "skip")
    print(f"  {col.at:>3} {col.txt:<22} {kind}  {role:<5}"
          f" n={col.n:<6} mid={show(col.mid())}")
  ok(min((c.n for c in t.x + t.y), default=1) > 0, True)   # none all "?"

def run(k):
  print(":" + k.lstrip("-").rstrip("_"))
  seed()
  eg[k]()

def main(argv):
  if not argv: return print(__doc__)
  for s in argv:
    if s in ("-h", "--help"): print(__doc__)
    elif s == "--all":
      for k in sorted(eg): run(k)
      print(f"PASS {len(eg)} tests")
    elif s in eg: run(s)
    elif (m := re.match(r"^(\w+)=(.*)$", s)):
      setattr(the, m[1], value(m[2]))
    else: the.file = s

if __name__ == "__main__": main(sys.argv[1:])
