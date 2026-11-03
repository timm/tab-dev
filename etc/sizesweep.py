#!/usr/bin/env python3
"""sizesweep.py: how many trees does a deep forest need?

`for60` ships 60 members on no stronger argument than an old curve
(bag=10/30/60/100 scoring 86.4/88.0/88.6/88.7 weak).  This re-asks it
at the deep settings we actually use -- depth=12 leaf=2, sqrt columns.

Members are NESTED, not refit: one 64-tree bag is grown, then scored
at its first 16, 32 and 64.  Bag draws each member's bootstrap in
turn, so the first 16 of a 64-bag ARE the 16-bag for that seed.  That
makes this a paired comparison -- the only thing changing is how many
of the same trees get to vote -- and costs one fit, not three.

Writes nothing to cache/.  usage: sizesweep.py [reps]
"""
import os, sys, time, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T
from ens import pair, macro, macroAuc, sqrtree

Moot = os.path.expanduser("~/gits/moot/classify")
Weak = "audiology anneal tic-tac-toe vowel car soybean vehicle balance.scale".split()
Ctrl = "trains labor weathernom zoo haberman diabetes sonar".split()
Size = (16, 32, 64)

class Sub:
  "The first N members of a bag, voting on their own."
  def __init__(i, all): i.all = all
  posts = T.Bag.posts                  # both read i.all and nothing
  guess = T.Bag.guess                  # else, so a slice just works

def one(file, reps):
  "Mean acc and macro auc at each size, plus seconds for the full bag."
  t = T.Tab(f"{Moot}/{file}.csv")
  got = {n: ([], []) for n in Size}
  secs = []
  for s in range(1, reps + 1):
    tr, te = pair(t, s)
    t0 = time.time()
    big  = T.Bag(tr, tr.rows, sqrtree, max(Size))
    secs.append(time.time() - t0)
    rows = tr.clone(te).rows
    want = [r[tr.klass.at] for r in rows]
    for n in Size:
      m     = Sub(big.all[:n])
      posts = [m.posts(r) for r in rows]
      got2  = [max(p, key=p.get) if p else want[0] for p in posts]
      got[n][0].append(float(macro(want, got2).split(",")[0]))
      got[n][1].append(float(macroAuc(want, posts).split(",")[0]))
  return ({n: (st.mean(a), st.mean(u)) for n, (a, u) in got.items()},
          st.mean(secs))

if __name__ == "__main__":
  reps = int(sys.argv[1]) if len(sys.argv) > 1 else 5
  T.the.depth, T.the.leaf = 12, 2
  tot = {n: ([], []) for n in Size}
  print(f"{'set':18s} " + " ".join(f"{n:>13d}" for n in Size) + "   secs(64)")
  for f in Weak + Ctrl:
    try: r, sec = one(f, reps)
    except Exception as e:
      print(f"FAIL {f}: {e}", flush=True); continue
    for n in Size:
      tot[n][0].append(r[n][0]); tot[n][1].append(r[n][1])
    print(f"{f:18s} " + " ".join(f"{r[n][0]:5.1f}/{r[n][1]:.3f}"
                                 for n in Size) + f"   {sec:7.2f}", flush=True)
  print(f"\nsets={len(tot[Size[0]][0])}  reps={reps}  depth=12 leaf=2 cols=sqrt")
  for n in Size:
    a, u = tot[n]
    print(f"  {n:3d} trees   acc={st.mean(a):5.2f}   auc={st.mean(u):.4f}")
