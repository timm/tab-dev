#!/usr/bin/env pypy3
"""sizes256.py: how many trees does tab2's capped forest need?

Members are NESTED, not refit, as in sizesweep.py: one forest of the
largest size is grown per split, then scored at its first 5, 10, 20,
... trees.  The first 30 of a 120-tree forest ARE the 30-tree forest
for that seed, so the only thing changing is how many of the same
trees get to vote -- a paired comparison for the price of one fit.

Splits and scores are py256.py's: min.py's shuffle, score.py's auc.

usage: pypy3 etc/sizes256.py out.csv f.csv     (REPS=5, SIZES=5,10,...)
       appends one line: set,rows,klasses, then auc and acc per size
"""
import os, sys, random, statistics as st
Here = os.path.dirname(os.path.abspath(__file__))
Dev  = os.path.dirname(Here)
sys.path.insert(0, Here)
sys.path.insert(0, os.getenv("TAB", os.path.join(os.path.dirname(Dev), "tab")))
import min as M
import tab2 as m
from score import macro, aucposts

Reps  = int(os.getenv("REPS", 5))
Sizes = [int(s) for s in os.getenv("SIZES", "5,10,20,30,60,120").split(",")]

def main(out, file):
  data = m.Tab(file)
  k    = data.klass
  if k is None or (isinstance(k, m.Num) and
                   len({r.raw[k.at] for r in data.rows}) > 30): return
  if len(M.Tbl(file).rows) != len(data.rows): return
  auc, acc = {s: [] for s in Sizes}, {s: [] for s in Sizes}
  for s in range(1, Reps + 1):
    M.the.Seed = 1234567891 + s
    rows = M.shuffle(data.rows[:])
    n    = int(.8 * len(rows))
    tr, te = rows[:n], rows[n:]
    random.seed(1234567891 + s)
    f    = m.Forest(data.clone(tr), rounds=max(Sizes))
    full = f.all
    want = [r.raw[k.at] for r in te]
    for z in Sizes:
      f.all = full[:z]
      a = aucposts(want, [f.posts(r) for r in te]).split(",")
      if int(a[1]) > 0: auc[z].append(float(a[0]))
      acc[z].append(float(macro(want, [f.guess(r) for r in te]).split(",")[0]))
  if not all(auc[z] for z in Sizes): return        # no auc on any rep
  name = file.split("/")[-1][:-4]
  line = f"{name},{len(data.rows)},{len(k.has)}," + ",".join(
           f"{st.fmean(auc[z]):.4f}" for z in Sizes) + "," + ",".join(
           f"{st.fmean(acc[z]):.2f}" for z in Sizes)
  with open(out, "a") as h: h.write(line + "\n")   # one short write: atomic

main(sys.argv[1], sys.argv[2])
