#!/usr/bin/env python3
"""rank.py: every arm's mean, on the sets they all finished.

An arm half way through a corpus looks better or worse than it is,
purely from which sets it has reached.  So compare only where every
named arm has a score.  usage: rank.py [col] arm ...
"""
import os, sys, statistics as st
Cache = os.path.expanduser(os.getenv("CACHE", "~/gh/tab-dev/cache"))

def mean(d, arm, col):
  p = f"{Cache}/classify/{d}/{arm}.csv"
  if not os.path.exists(p): return None
  with open(p) as f:
    h = f.readline().strip().split(",")
    if col not in h: return None
    j = h.index(col)
    v = [float(l.split(",")[j]) for l in f if l.strip()]
  return st.mean(v) if v else None

def main(col, arms):
  sets = sorted(os.listdir(f"{Cache}/classify"))
  got  = {a: {s: m for s in sets if (m := mean(s, a, col)) is not None}
          for a in arms}
  for a in arms: print(f"  {a:10s} has {len(got[a]):3d} sets")
  common = set(sets)
  for a in arms: common &= set(got[a])
  print(f"\non the {len(common)} sets every arm finished:")
  ref = arms[-1]
  eps = .005 if col in ("auc", "d2h") else .5   # auc lives in [0,1], so
  lo  = col in ("pf", "d2h")                    # a 0.5 tie band would
  for a in arms:                                # call every set a tie;
    mu = st.mean([got[a][s] for s in common])   # and for pf and d2h a
    hi = [s for s in common if got[a][s] > got[ref][s] + eps]  # bigger
    lt = [s for s in common if got[ref][s] > got[a][s] + eps]  # number
    w, l = (len(lt), len(hi)) if lo else (len(hi), len(lt))    # is WORSE
    print(f"  {a:10s} {col}={mu:6.3f}   vs {ref}: win={w:3d} "
          f"tie={len(common)-w-l:3d} loss={l:3d}")
  best = {}
  for s in common:
    b = (min if lo else max)(arms, key=lambda a: got[a][s])
    best[b] = best.get(b, 0) + 1
  print("\nbest arm per set: " + "  ".join(f"{a}={n}"
        for a, n in sorted(best.items(), key=lambda kv: -kv[1])))

if __name__ == "__main__":
  a = sys.argv[1:]
  col = a.pop(0) if a and a[0] in ("acc","auc","pd","pf","d2h") else "acc"
  main(col, a)
