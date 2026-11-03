#!/usr/bin/env python3
"""ens.py: bag or boost tab's own learners, scored like every other arm.

The record says the gap to LightGBM is bias, not variance: nb=80.1 and
one tab tree=74.4 against lgbm=82.6.  Bagging naive bayes was measured
over 73 sets and moved nothing (-0.04).  So this bags and boosts the
TREE, whose single score is the worst of the three but whose errors are
the least like each other -- and, since `rounds` members of a bag are
themselves a learner, boosts a bag of them.

A split is a seed: `rint` here is `min.py`'s and `min.lua`'s, so these
are the rows nb, lgbm and tabicl saw.  Test rows bin on TRAINING
statistics.  Writes <cache>/<set>/<arm>.csv and <arm>auc.csv in the
format every other arm writes, so charts.py can draw it.

usage: ens.py arm f.csv ...   arms: see Arms (deep ones are best)
"""
import sys, os, time, math
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import auc1

Cache = os.path.expanduser(os.getenv("CACHE", "~/gh/tab-dev/cache"))
Reps  = int(os.getenv("REPS", "20"))

def home(f):
  "Where this data set's scores live, mirroring moot's tree."
  return f"{Cache}/{f.split('moot/')[-1][:-4]}"

def pair(t, s):
  "Rep S's two halves, from the seed alone -- min.py's own shuffle."
  T.seed(1234567891 + s)
  rows = t.rows[:]
  for i in range(len(rows), 1, -1):
    j = T.rint(i)
    rows[i - 1], rows[j - 1] = rows[j - 1], rows[i - 1]
  n = int(.8 * len(rows))
  return t.clone(rows[:n]), rows[n:]

def deep(tab, rows):
  "Depth enough to name every klass, plus one -- as tree-eg.lua does."
  ks, d = len({r[tab.klass.at] for r in rows}), 2
  while 2 ** (d - 1) < ks: d += 1
  return max(T.the.depth, d + 1)

def tree(cols=0):
  "A Tree as a base learner: the klass for y, a Sym to collect it."
  def fit(tab, rows):
    b4, T.the.depth = T.the.depth, deep(tab, rows)
    try:
      return T.Tree(tab, rows, [r[tab.klass.at] for r in rows],
                    T.Sym, cols)
    finally: T.the.depth = b4
  return fit

def knobs(fit, depth, leaf):
  """FIT, but grown deep.  tab ships depth=4 leaf=8, so a tree holds at
  most 8 leaves -- it cannot even name audiology's 24 klasses, and on a
  14-row set `2*leaf` exceeds the data so nothing splits at all.  A
  sweep (etc/knobs.py) puts the plateau at depth=12 leaf=2: +13 on the
  many-klass sets, and the variance it adds on the noisy ones
  (diabetes, haberman) is exactly what a bag removes."""
  def go(tab, rows):
    b4 = T.the.depth, T.the.leaf
    T.the.depth, T.the.leaf = depth, leaf
    try: return fit(tab, rows)
    finally: T.the.depth, T.the.leaf = b4
  return go

def sqrtree(tab, rows):
  "A bag member: looking at sqrt(#x) columns, as a random forest does."
  return tree(max(1, int(len(tab.x) ** .5)))(tab, rows)

# (fit, bins): naive bayes counts, so it needs its columns binned.  A
# tree does not -- and binning first throws away the ordering that a
# NUM cut lives on, so the raw arms are the interesting ones.
Arms = {
  "forest":   (lambda t, r: T.Bag(t, r, tree(3), 30),            1),
  "boostree": (lambda t, r: T.Boost(t, r, tree(0), 20),          1),
  "bagboost": (lambda t, r: T.Boost(t, r,        # boosting AFTER
                   lambda t2, r2: T.Bag(t2, r2, tree(3), 5), 10), 1),
  "bagnb":    (lambda t, r: T.Bag(t, r, T.Nb, 30),               1),
  "nb":       (lambda t, r: T.Nb(t, r),                          1),
  "treeraw":  (lambda t, r: tree(0)(t, r),                       0),
  "forraw":   (lambda t, r: T.Bag(t, r, tree(3), 30),            0),
  "forraw0":  (lambda t, r: T.Bag(t, r, tree(0), 30),            0),
  "boostraw": (lambda t, r: T.Boost(t, r, tree(0), 20),          0),
  "bagboraw": (lambda t, r: T.Boost(t, r,
                   lambda t2, r2: T.Bag(t2, r2, tree(3), 5), 10), 0),
  # deep: same shapes, but the tree is allowed to grow (see `knobs`)
  "treedeep": (knobs(lambda t, r: tree(0)(t, r),         12, 2),  0),
  "fordeep":  (knobs(lambda t, r:
                   T.Bag(t, r, sqrtree, 30), 12, 2),              0),
  "fordeep0": (knobs(lambda t, r:
                   T.Bag(t, r, tree(0), 30), 12, 2),              0),
  "for60":    (knobs(lambda t, r:
                   T.Bag(t, r, sqrtree, 60), 12, 2),              0),
  "boostdeep":(knobs(lambda t, r:
                   T.Boost(t, r, tree(0), 20),  8, 2),            0),
  "either":   (lambda t, r: Either(t, r, knobs(lambda t2, r2:
                   T.Bag(t2, r2, sqrtree, 30), 12, 2)),           0),
  "either60": (lambda t, r: Either(t, r, knobs(lambda t2, r2:
                   T.Bag(t2, r2, sqrtree, 60), 12, 2)),           0),
  "hardeep":  (knobs(lambda t, r:                # fordeep, but the
                   Hard(t, r, sqrtree, 30), 12, 2),  0),  # vote is hard
  "bagbodeep":(knobs(lambda t, r: T.Boost(t, r,
                   lambda t2, r2: T.Bag(t2, r2, sqrtree, 5), 10),
                   12, 2),                                        0)}

class Hard:
  """A deep forest that votes LABELS, not distributions.

  Same members as `fordeep` -- same bootstraps, same sqrt columns,
  same depth and leaf -- so the only thing changed is how they are
  combined: each tree contributes one vote for its leaf's majority,
  where `Bag` would have contributed that leaf's whole distribution.
  `posts` is then the share of the vote, which is what lets an auc be
  taken at all; drop it and a tree arm has no ranking to report."""
  def __init__(i, tab, rows, Learn, rounds):
    i.all = [Learn(tab, T.some(rows, len(rows))) for _ in range(rounds)]
  def posts(i, row,    votes=None):
    votes = {}
    for m in i.all:
      k = m.guess(row)
      if k is not None: votes[k] = votes.get(k, 0) + 1
    z = sum(votes.values()) or 1
    return {k: v / z for k, v in votes.items()}
  def guess(i, row,    p=None):
    p = i.posts(row)
    return max(p, key=p.get) if p else None

class Either:
  """Naive Bayes or a deep forest, chosen on the TRAINING rows alone.

  The per-set record says each owns a different kind of data: NB wins
  the small noisy ones (heart.c 87.4 vs a deep tree's 74.3) and the
  forest wins the large structured ones (letter 82.2 vs NB's 70.2).  So
  hold out a quarter of train, score both on it, refit the winner on
  all of train.  No test row is touched -- the choice is a learner, not
  a result."""
  def __init__(i, tab, rows, Learn, frac=.75):
    i.tab = tab
    n  = max(2, int(frac * len(rows)))
    tr, va = rows[:n], rows[n:] or rows[:]     # pair() already shuffled
    nb, fo = i.fit(tr, Learn)
    i.who  = ("nb" if i.score(nb, va, 1) >= i.score(fo, va, 0) else "fo")
    nb, fo = i.fit(rows, Learn)                # then refit on all of it
    i.m, i.bins = (nb, 1) if i.who == "nb" else (fo, 0)

  def fit(i, rows, Learn):
    "Both learners on ROWS: NB needs bins, the forest wants raw."
    b = i.tab.binned(rows)
    return T.Nb(b, b.rows), Learn(i.tab.clone(rows), rows)

  def bin(i, row):
    return [c.bin(row[c.at]) for c in i.tab.cols]

  def score(i, m, rows, bins     , ok=0):
    "Accuracy on the held-out slice, each learner seeing its own rows."
    for r in rows:
      p = m.posts(i.bin(r) if bins else r)
      if p and max(p, key=p.get) == r[i.tab.klass.at]: ok += 1
    return ok / len(rows)

  def posts(i, row):
    return i.m.posts(i.bin(row) if i.bins else row)

  def guess(i, row):
    p = i.posts(row)
    return max(p, key=p.get) if p else None

def macro(want, got):
  "Accuracy, then abcd's macro pd, pf and d2h -- lgbm.py's own code."
  n, ok, ws, gs, hs = len(want), 0, {}, {}, {}
  for a, b in zip(want, got):
    a, b = str(a), str(b)
    ok += a == b
    ws[a] = ws.get(a, 0) + 1
    gs[b] = gs.get(b, 0) + 1
    if a == b: hs[a] = hs.get(a, 0) + 1
  pd = pf = d2h = 0
  for x, w in ws.items():
    tp = hs.get(x, 0); fp = gs.get(x, 0) - tp; fn = w - tp
    tn = n - fn - fp - tp
    r1 = tp / (tp + fn)
    f1 = fp / (fp + tn) if fp + tn else 0
    pd += r1; pf += f1; d2h += ((1-r1)**2 + f1**2) ** .5 / 2 ** .5
  k = len(ws)
  return f"{100*ok/n:.1f},{100*pd/k:.1f},{100*pf/k:.1f},{d2h/k:.3f}"

def macroAuc(want, posts):
  "Macro mean of each klass's one-against-the-rest auc, and its count."
  ks  = sorted({k for p in posts for k in p}, key=str)   # a klass may
  out = [a for k in ks                                   # be an int, so
         if (a := auc1([p.get(k, 0) for p in posts],     # look it up as
                       [str(w) == str(k) for w in want]  # itself, and
                       )) is not None]                   # compare as text
  return f"{sum(out)/len(out):.4f},{len(out)}" if out else "0,0"

def one(arm, file):
  t = T.Tab(file)
  if not t.klass: return print(f"skip {file}: no klass", file=sys.stderr)
  d = home(file)
  os.makedirs(d, exist_ok=True)
  acc = [f"rep,secs,acc,pd,pf,d2h"]
  auc = [f"rep,secs,auc,klasses"]
  for s in range(1, Reps + 1):
    tr, te = pair(t, s)
    fit, bins = Arms[arm]
    btr = tr.binned(tr.rows) if bins else tr
    bte = tr.binned(te)      if bins else tr.clone(te)
    t0 = time.time()
    m  = fit(btr, btr.rows)
    want  = [r[tr.klass.at] for r in bte.rows]
    posts = [m.posts(r) for r in bte.rows]
    got   = [max(p, key=p.get) for p in posts]
    secs  = time.time() - t0
    acc.append(f"{s},{secs:.4f},{macro(want, got)}")
    auc.append(f"{s},{secs:.4f},{macroAuc(want, posts)}")
  open(f"{d}/{arm}.csv", "w").write("\n".join(acc) + "\n")
  open(f"{d}/{arm}auc.csv", "w").write("\n".join(auc) + "\n")
  print(f"{os.path.basename(file)[:22]:24s} {arm:9s} "
        f"acc={sum(float(l.split(',')[2]) for l in acc[1:])/Reps:5.1f} "
        f"auc={sum(float(l.split(',')[2]) for l in auc[1:])/Reps:.3f}",
        flush=True)

if __name__ == "__main__":
  arm = sys.argv[1]
  for f in sys.argv[2:]:
    try: one(arm, f)
    except Exception as e:
      print(f"FAIL {os.path.basename(f)}: {e}", file=sys.stderr, flush=True)
