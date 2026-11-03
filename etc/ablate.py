#!/usr/bin/env python3
"""ablate.py: what can the deep forest lose and not miss?

The forest reached LightGBM by stacking four ideas on tab's tree:
grow it deep, bootstrap the rows, subsample the columns, and average
the leaf distributions.  Each was added because it helped SOMETHING.
This takes them away one at a time and asks whether the set-level
score actually notices, and what the removal buys back in seconds.

Every arm sees the same 80:20 splits (`pair`, seeded), so this is
paired: a difference here is the ablation, not the draw.  Baseline is
the `for60` recipe at the size sizesweep.py settled on.

Writes nothing to cache/.  usage: ablate.py [reps] [arm ...]
"""
import os, sys, time, math, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T
from ens import pair, macro, macroAuc

Moot  = os.path.expanduser("~/gits/moot/classify")
Weak  = "audiology anneal tic-tac-toe vowel car soybean vehicle balance.scale".split()
# `trains` is 10 rows -- 2 test rows per split, so its auc swings
# between .55 and 1.00 on nothing.  charts.py's auc() already drops it.
Ctrl  = "labor weathernom zoo haberman diabetes sonar".split()
Rounds = int(os.getenv("ROUNDS", 32))      # what sizesweep.py settled

# ---- the knobs, each defaulting to the baseline recipe -------------
def mktree(cols):
  """A tree as a base learner.  COLS: 'sqrt', or an int (0 = all).
  ens.py's `tree`, inlined so `deep` cannot also move underneath us."""
  def fit(tab, rows):
    c = max(1, int(math.sqrt(len(tab.x)))) if cols == "sqrt" else cols
    return T.Tree(tab, rows, [r[tab.klass.at] for r in rows], T.Sym, c)
  return fit

def draw(rows, boot):
  "The rows one member trains on.  'full': a bootstrap.  'none': all."
  if boot == "none": return rows
  if boot == "full": return T.some(rows, len(rows))
  n = int(float(boot) * len(rows))         # a fraction, no replacement
  return T.pick(rows, n)

class Forest:
  "A bag, with the vote and the sampling left open."
  def __init__(i, tab, rows, Learn, rounds, boot, vote):
    i.vote = vote
    i.all  = [Learn(tab, draw(rows, boot)) for _ in range(rounds)]
  def posts(i, row):
    "Soft: average the leaf distributions.  Hard: count the labels."
    sums = {}
    if i.vote == "hard":
      for m in i.all:
        k = m.guess(row)
        if k is not None: sums[k] = sums.get(k, 0) + 1
    else:
      for m in i.all:
        for k, p in m.posts(row).items(): sums[k] = sums.get(k, 0) + p
    z = sum(sums.values()) or 1
    return {k: v / z for k, v in sums.items()}

def fewcuts(k):
  """A NUM cut that offers K candidate splits, not one per distinct
  value.  `the.bins` does NOT reach the tree -- it only feeds
  `Tab.binned`, so a tree sweeps every value and `Tab.cut` pays an
  entropy per candidate.  This is the knob that actually exists."""
  def cut(i, xy, Y,    near=None, far=None):
    xy.sort(key=lambda p: p[0])
    n = len(xy)
    near, far = Y(), Y()
    for _, y in xy: far.add(y)
    step = max(1, n // k)                # every step-th row is a
    for j, (x, y) in enumerate(xy[:-1]): # candidate, if it ends a run
      near.add(y); far.add(y, -1)
      if x != xy[j + 1][0] and (j + 1) % step == 0:
        yield near, far, x
  return cut

def mkarm(cols="sqrt", boot="full", vote="soft", rounds=None,
          depth=12, leaf=2, bins=None, cuts=0, Learn=None):
  """A fitter, plus the `the` settings it wants while it runs.

  LEARN names the base learner: None (a tree) or T.Nb.  An Nb counts,
  so its arm is marked `wantbins` below and gets binned columns; a
  tree takes the raw ones, where a NUM cut can still see order."""
  def fit(tab, rows,    b4=None):
    b4 = T.the.depth, T.the.leaf, T.the.bins, T.Num.cut
    T.the.depth, T.the.leaf = depth, leaf
    if bins: T.the.bins = bins
    if cuts: T.Num.cut = fewcuts(cuts)
    try:
      return Forest(tab, rows, Learn or mktree(cols),
                    rounds or Rounds, boot, vote)
    finally:
      T.the.depth, T.the.leaf, T.the.bins = b4[:3]
      T.Num.cut = b4[3]
  return fit

Arms = {
  "base":      mkarm(),                      # deep, bootstrap, sqrt, soft
  "hardvote":  mkarm(vote="hard"),           # drop the distributions
  "allcols":   mkarm(cols=0),                # drop the column subsample
  "noboot":    mkarm(boot="none"),           # drop the bootstrap
  "boot632":   mkarm(boot="0.632"),          # subsample, no replacement
  "shallow":   mkarm(depth=8),               # drop four levels
  "leaf4":     mkarm(leaf=4),                # stop splitting sooner
  "cut8":      mkarm(cuts=8),                # 8 candidate splits, not n
  "cut16":     mkarm(cuts=16),
  "onetree":   mkarm(rounds=1, cols=0, boot="none"),       # the floor
  "cut8tree":  mkarm(rounds=1, cols=0, boot="none", cuts=8),
  "nb":        mkarm(rounds=1, boot="none", Learn=T.Nb),   # one Nb
  "nb32":      mkarm(Learn=T.Nb),                          # 32 of them
}

Wantbins = {"nb", "nb32"}            # counters, so they need bins

def one(fit, file, reps, bins=False):
  "Mean acc, macro auc and fit seconds over REPS splits of FILE."
  t = T.Tab(f"{Moot}/{file}.csv")
  accs, aucs, secs = [], [], []
  for s in range(1, reps + 1):
    tr, te = pair(t, s)
    btr = tr.binned(tr.rows) if bins else tr    # test rows bin on
    t0   = time.time()                          # TRAINING stats
    m    = fit(btr, btr.rows)
    secs.append(time.time() - t0)
    rows  = (tr.binned(te) if bins else tr.clone(te)).rows
    want  = [r[tr.klass.at] for r in rows]
    posts = [m.posts(r) for r in rows]
    got   = [max(p, key=p.get) if p else want[0] for p in posts]
    accs.append(float(macro(want, got).split(",")[0]))
    aucs.append(float(macroAuc(want, posts).split(",")[0]))
  return st.mean(accs), st.mean(aucs), st.mean(secs)

if __name__ == "__main__":
  reps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
  want = sys.argv[2:] or list(Arms)
  files = Weak + Ctrl
  got = {a: {} for a in want}
  for a in want:
    T.seed()                               # every arm, the same stream
    for f in files:
      try: got[a][f] = one(Arms[a], f, reps, a in Wantbins)
      except Exception as e:
        print(f"FAIL {a} {f}: {e}", file=sys.stderr, flush=True)
    acc = st.mean([v[0] for v in got[a].values()])
    auc = st.mean([v[1] for v in got[a].values()])
    sec = st.mean([v[2] for v in got[a].values()])
    print(f"{a:10s} acc={acc:5.2f} auc={auc:.4f} secs={sec:6.3f} "
          f"sets={len(got[a])}", flush=True)
    for f in files:
      if f in got[a]:
        print(f"    {f:16s} {got[a][f][0]:5.1f}/{got[a][f][1]:.3f}"
              f" {got[a][f][2]:7.3f}", flush=True)
  # per-set deltas against base, so a mean cannot hide a wrecked set
  if "base" in got:
    print(f"\n{'arm':10s} {'dacc':>7s} {'dauc':>8s} {'xspeed':>7s}"
          f"  {'worst set (dacc)':>28s}")
    b = got["base"]
    for a in want:
      if a == "base": continue
      ks = [f for f in b if f in got[a]]
      da = st.mean([got[a][f][0] - b[f][0] for f in ks])
      du = st.mean([got[a][f][1] - b[f][1] for f in ks])
      sp = (st.mean([b[f][2] for f in ks])
            / max(1e-9, st.mean([got[a][f][2] for f in ks])))
      w  = min(ks, key=lambda f: got[a][f][0] - b[f][0])
      print(f"{a:10s} {da:+7.2f} {du:+8.4f} {sp:6.2f}x"
            f"  {w:>18s} {got[a][w][0]-b[w][0]:+6.1f}")
