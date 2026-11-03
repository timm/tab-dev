#!/usr/bin/env python3
"""knobs.py: does depth/leaf/cols starvation explain our weak sets?

ens.py runs every tree at tab's shipped depth=4 leaf=8.  A depth-4 tree
has at most 8 leaves, so a 24-klass set like audiology cannot even NAME
its klasses, and leaf=8 stops any split at all on a 14-row set.  The
sets we lose worst on are exactly the many-klass ones, so this sweeps
depth, leaf and the column subsample over a weak slice plus a control
slice -- and writes nothing to cache/, so the record stays clean.

usage: knobs.py arm [reps]      arm: forraw bagboraw treeraw
"""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/gh/tab"))
import tab as T
from ens import pair, macro, macroAuc, tree

Moot = os.path.expanduser("~/gits/moot/classify")
Weak = "audiology anneal tic-tac-toe vowel car soybean vehicle balance.scale".split()
Ctrl = "trains labor weathernom zoo haberman diabetes sonar".split()
Grid = [(4, 8, 0), (8, 4, 0), (8, 2, 0), (12, 2, 0), (16, 2, 0),
        (4, 8, 3), (8, 2, 3), (12, 2, 3), (12, 2, -1)]

def treesq(tab, rows):
  "A tree whose column subsample is sqrt(#x), as a random forest's is."
  import math
  return tree(max(1, int(math.sqrt(len(tab.x)))))(tab, rows)

def arm(name, cols):
  "The ens.py arms, but with the column subsample as a parameter."
  fit = treesq if cols == -1 else tree(cols)
  if name == "treeraw":  return lambda t, r: fit(t, r)
  if name == "forraw":   return lambda t, r: T.Bag(t, r, fit, 30)
  if name == "bagboraw": return lambda t, r: T.Boost(
      t, r, lambda t2, r2: T.Bag(t2, r2, fit, 5), 10)
  raise Exception(f"no arm {name}")

def one(fit, file, reps):
  "Mean accuracy and macro auc over REPS splits of FILE."
  t = T.Tab(f"{Moot}/{file}.csv")
  accs, aucs = [], []
  for s in range(1, reps + 1):
    tr, te = pair(t, s)
    m     = fit(tr, tr.rows)
    rows  = tr.clone(te).rows
    want  = [r[tr.klass.at] for r in rows]
    posts = [m.posts(r) for r in rows]
    got   = [max(p, key=p.get) if p else want[0] for p in posts]
    accs.append(float(macro(want, got).split(",")[0]))
    aucs.append(float(macroAuc(want, posts).split(",")[0]))
  return st.mean(accs), st.mean(aucs)

if __name__ == "__main__":
  name = sys.argv[1]
  reps = int(sys.argv[2]) if len(sys.argv) > 2 else 5
  for depth, leaf, cols in Grid:
    T.the.depth, T.the.leaf = depth, leaf
    fit, out = arm(name, cols), {}
    for f in Weak + Ctrl:
      try: out[f] = one(fit, f, reps)
      except Exception as e: out[f] = (float("nan"), float("nan"))
      print(f"  depth={depth} leaf={leaf} cols={cols} {f:16s} "
            f"acc={out[f][0]:5.1f} auc={out[f][1]:.3f}", flush=True)
    w = st.mean([out[f][0] for f in Weak])
    c = st.mean([out[f][0] for f in Ctrl])
    print(f"{name} depth={depth} leaf={leaf} cols={cols}  "
          f"weak={w:5.2f} ctrl={c:5.2f}", flush=True)
