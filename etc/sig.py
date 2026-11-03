#!/usr/bin/env python3
"""sig.py: is one arm really better than another, or is it seed noise?

House style is min.py's three tests -- Cohen's d, Cliff's delta and a
KS -- and `same` only calls two arms different when all three agree.
Those are unpaired, so this also reports the paired view: per-set
deltas, since the same 73 sets score every arm.

usage: sig.py [col] armA armB ...   (each arm is tested against the last)
"""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from min import cohen, cliffs, ks, same
from rank import mean

Cache = os.path.expanduser(os.getenv("CACHE", "~/gh/tab-dev/cache"))

def main(col, arms):
  sets = sorted(os.listdir(f"{Cache}/classify"))
  got  = {a: {s: m for s in sets if (m := mean(s, a, col)) is not None}
          for a in arms}
  common = set(sets)
  for a in arms: common &= set(got[a])
  common, ref = sorted(common), arms[-1]
  lo = col in ("pf", "d2h")            # pf and d2h: smaller is better
  print(f"{len(common)} sets, {col} ({'lower' if lo else 'higher'} "
        f"is better), every arm against {ref}:\n")
  for a in arms[:-1]:
    xs = [got[a][s]   for s in common]
    ys = [got[ref][s] for s in common]
    ds = [x - y for x, y in zip(xs, ys)]
    better = (lambda d: d < 0) if lo else (lambda d: d > 0)
    win  = sum(1 for d in ds if better(d))
    tie  = sum(1 for d in ds if d == 0)
    loss = len(ds) - win - tie
    print(f"  {a:10s} {st.mean(xs):6.3f} vs {st.mean(ys):6.3f}  "
          f"delta mean={st.mean(ds):+6.3f} median={st.median(ds):+6.3f}\n"
          f"  {'':10s} cohen={cohen(xs, ys):.3f} "
          f"cliffs={cliffs(sorted(xs), sorted(ys)):.3f} "
          f"ks={ks(sorted(xs), sorted(ys)):.3f} -> "
          f"{'same' if same(xs, ys) else 'DIFFERENT'} (unpaired)\n"
          f"  {'':10s} paired: wins={win} ties={tie} losses={loss}\n")

if __name__ == "__main__":
  a = sys.argv[1:]
  col = a.pop(0) if a and a[0] in ("acc","auc","pd","pf","d2h") else "acc"
  main(col, a)
