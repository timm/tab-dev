#!/usr/bin/env python3
"""closer.py: can an ensemble of tab's own learners close on LightGBM?

The record says nb=80.1, one tab tree=74.4, lgbm=82.6 -- so the gap is
bias, not variance, and bagging naive bayes cannot touch it.  This asks
the other question: bag or boost the TREE, whose single-model score is
the worst of the three but whose errors are the most independent.

Every arm sees identical 80:20 splits and test rows binned on TRAINING
statistics.  LightGBM runs here too, so no number comes from a cache
built by a different rig.  usage: closer.py seeds f.csv ...
"""
import sys, os, statistics as st
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T

def split(rows, seed):
  T.seed(seed); u = rows[:]
  for j in range(len(u) - 1, 0, -1):
    k = T.rint(j + 1) - 1; u[j], u[k] = u[k], u[j]
  n = int(.8 * len(u))
  return u[:n], u[n:]

def klassy(cols=0, slack=1):
  """A Tree as a base learner.  A depth-4 binary tree has 8 leaves, so
  it cannot even name soybean's 19 klasses -- grow deep enough to say
  them all, plus SLACK, which is what tree-eg.lua's ktree does."""
  def fit(tab, rows):
    ks, d = len({r[tab.klass.at] for r in rows}), 2
    while 2 ** (d - 1) < ks: d += 1
    b4, T.the.depth = T.the.depth, max(T.the.depth, d + slack)
    try:
      return T.Tree(tab, rows, [r[tab.klass.at] for r in rows],
                    T.Sym, cols)
    finally:
      T.the.depth = b4                   # never leave `the` changed
  return fit

def lgbm(tr, te):
  "LightGBM on the same split, raw columns, label-encoded."
  from lightgbm import LGBMClassifier
  at = tr.klass.at
  xs = [c.at for c in tr.x]
  enc = {}
  def row(r):
    out = []
    for j in xs:
      v = r[j]
      if isinstance(v, str):
        enc.setdefault(j, {}).setdefault(v, len(enc.setdefault(j, {})))
        v = enc[j][v]
      out.append(-1 if v == "?" else v)
    return out
  X, y = [row(r) for r in tr.rows], [r[at] for r in tr.rows]
  m = LGBMClassifier(verbose=-1, n_estimators=100).fit(X, y)
  p = m.predict([row(r) for r in te])
  return 100 * sum(a == b[at] for a, b in zip(p, te)) / len(te)

def score(fit, tr, te):
  at, btr, bte = tr.klass.at, tr.binned(tr.rows), tr.binned(te)
  m = fit(btr, btr.rows)
  return 100 * sum(m.guess(r) == r[at] for r in bte.rows) / len(bte.rows)

def main(seeds, files):
  arms = {
    "nb":      lambda t, r: T.Nb(t, r),
    "tree":    klassy(),
    "forest":  lambda t, r: T.Bag(t, r, klassy(3), 30),
    "bagnb":   lambda t, r: T.Bag(t, r, T.Nb, 30),
    "boostnb": lambda t, r: T.Boost(t, r, T.Nb, 20),
    "boostree":lambda t, r: T.Boost(t, r, klassy(), 20)}
  tot = {k: [] for k in list(arms) + ["lgbm"]}
  for f in files:
    t = T.Tab(f)
    if not t.klass or len(t.rows) < 40: continue
    got = {k: [] for k in tot}
    for s in range(1, seeds + 1):
      a, b = split(t.rows, 1234567891 + s)
      tr   = t.clone(a)
      for k, fit in arms.items(): got[k].append(score(fit, tr, b))
      got["lgbm"].append(lgbm(tr, b))
    for k in got: tot[k].append(st.mean(got[k]))
    print(f"{os.path.basename(f)[:18]:20s}"
          + " ".join(f"{k}={st.mean(got[k]):5.1f}" for k in tot),
          flush=True)
  print(f"\nsets={len(tot['nb'])}")
  for k in tot:
    mu = st.mean(tot[k])
    w = sum(1 for x, y in zip(tot[k], tot["lgbm"]) if x - y > .5)
    l = sum(1 for x, y in zip(tot[k], tot["lgbm"]) if y - x > .5)
    print(f"  {k:9s} {mu:6.2f}  vs lgbm: win={w:3d} "
          f"tie={len(tot[k])-w-l:3d} loss={l:3d}")

if __name__ == "__main__":
  main(int(sys.argv[1]), sys.argv[2:])
