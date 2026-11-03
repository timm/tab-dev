#!/usr/bin/env python3
"""ensemble.py: does bagging or boosting help naive bayes?

One 80:20 holdout per seed, test rows binned on TRAINING statistics
(the +2.5 finding in CLAUDE.md).  Every arm gets the same splits, so
the only difference is the learner.  Prints one line per data set,
then a summary.  usage: ensemble.py [seeds] [file.csv ...]
"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/gh/tab"))   # the library,
import tab as T                                      # not our stale copy

def split(rows, seed):
  "Fisher-Yates with tab's own rint, so the split is a seed."
  T.seed(seed)
  u = rows[:]
  for j in range(len(u) - 1, 0, -1):
    k = T.rint(j + 1) - 1
    u[j], u[k] = u[k], u[j]
  n = int(.8 * len(u))
  return u[:n], u[n:]

def score(Learn, tr, te):
  "Accuracy of LEARN, trained on TR, asked of TE."
  at  = tr.klass.at
  btr = tr.binned(tr.rows)
  bte = tr.binned(te)                     # TRAINING stats, not test
  m   = Learn(btr, btr.rows)
  hits = sum(m.guess(r) == r[at] for r in bte.rows)
  return 100 * hits / len(bte.rows)

def arms():
  return {"nb":    T.Nb,
          "bag":   lambda tab, rows: T.Bag(tab, rows, T.Nb),
          "boost": lambda tab, rows: T.Boost(tab, rows, T.Nb)}

def main(seeds, files):
  tot, won = {k: [] for k in arms()}, {"bag": [0,0,0], "boost": [0,0,0]}
  for f in files:
    try: t = T.Tab(f)
    except Exception as e: print(f"skip {f}: {e}", file=sys.stderr); continue
    if not t.klass: continue
    got = {k: [] for k in arms()}
    for s in range(1, seeds + 1):
      a, b = split(t.rows, 1234567891 + s)
      tr   = t.clone(a)
      for k, Learn in arms().items(): got[k].append(score(Learn, tr, b))
    mu = {k: sum(v) / len(v) for k, v in got.items()}
    for k in mu: tot[k].append(mu[k])
    for k in ("bag", "boost"):
      d = mu[k] - mu["nb"]
      won[k][0 if d > .5 else 2 if d < -.5 else 1] += 1
    print(f"{os.path.basename(f)[:26]:28s} rows={len(t.rows):6d} "
          + "  ".join(f"{k}={mu[k]:5.1f}" for k in ("nb","bag","boost")))
  print()
  print("sets=%d  " % len(tot["nb"])
        + "  ".join(f"{k}={sum(v)/len(v):5.2f}" for k, v in tot.items()))
  for k in ("bag", "boost"):
    print(f"{k:6s} vs nb: win={won[k][0]} tie={won[k][1]} loss={won[k][2]}")

if __name__ == "__main__":
  a = sys.argv[1:]
  n = int(a[0]) if a and a[0].isdigit() else 5
  main(n, a[1:] if not (a and a[0].isdigit()) else a[1:])
