#!/usr/bin/env python3
"""bagsweep.py: bagging knobs against plain naive bayes.

Same 80:20 splits for every arm; test rows binned on TRAINING stats.
Arms: nb, then Bag at each (rounds, size), soft (average the posts)
and hard (majority of the labels).
usage: bagsweep.py [seeds] file.csv ...
"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T

class Hard(T.Bag):                       # same bags, labels only
  def guess(i, row):
    votes = {}
    for m in i.all:
      k = m.guess(row); votes[k] = votes.get(k, 0) + 1
    return max(votes, key=votes.get)

def split(rows, seed):
  T.seed(seed); u = rows[:]
  for j in range(len(u) - 1, 0, -1):
    k = T.rint(j + 1) - 1; u[j], u[k] = u[k], u[j]
  n = int(.8 * len(u))
  return u[:n], u[n:]

def score(Learn, tr, te):
  at, btr, bte = tr.klass.at, tr.binned(tr.rows), tr.binned(te)
  m = Learn(btr, btr.rows)
  return 100 * sum(m.guess(r) == r[at] for r in bte.rows) / len(bte.rows)

ARMS = {"nb": T.Nb}
for R in (10, 30):
  for S in (0.3, 0.6, 1.0):
    ARMS[f"soft{R}/{S}"] = (lambda R, S: lambda t, r:
                            T.Bag(t, r, T.Nb, R, S))(R, S)
ARMS["hard10/1.0"] = lambda t, r: Hard(t, r, T.Nb, 10, 1.0)

def main(seeds, files):
  tot = {k: [] for k in ARMS}
  for f in files:
    t = T.Tab(f)
    if not t.klass: continue
    got = {k: [] for k in ARMS}
    for s in range(1, seeds + 1):
      a, b = split(t.rows, 1234567891 + s)
      tr = t.clone(a)
      for k, L in ARMS.items(): got[k].append(score(L, tr, b))
    for k in got: tot[k].append(sum(got[k]) / seeds)
    print(f"{os.path.basename(f)[:20]:22s}"
          + " ".join(f"{k}={sum(got[k])/seeds:5.1f}" for k in ARMS),
          flush=True)
  print(f"\nsets={len(tot['nb'])}")
  base = sum(tot["nb"]) / len(tot["nb"])
  for k in ARMS:
    mu = sum(tot[k]) / len(tot[k])
    w = sum(1 for x, y in zip(tot[k], tot["nb"]) if x - y > .5)
    l = sum(1 for x, y in zip(tot[k], tot["nb"]) if y - x > .5)
    print(f"  {k:12s} {mu:6.2f}  ({mu-base:+5.2f})  win={w:3d} loss={l:3d}")

if __name__ == "__main__":
  a = sys.argv[1:]
  main(int(a[0]), a[1:])
