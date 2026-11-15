#!/usr/bin/env pypy3
"""py256.py: tab2.py's forest, over the lua arms' splits, scored their way.

The forest that pdpf.png and auc.png report: 30 trees, each trained on
at most `cap` rows of any one klass (tab2's default, 256).  It writes
the same two files every classify arm writes, so charts.py reads it
like any other:

    <cache>/classify/<set>/py256.csv      acc, pd, pf, d2h, ...
    <cache>/classify/<set>/py256auc.csv   auc, klasses, macroauc

A split is a seed, not a file: `min.py`'s Park-Miller `shuffle` is the
one in tab.lua, so rep s here tests on the rows rep s tested on for
`hardhist`, `lgbm` and `tabicl`.  The scores are `score.py`'s, the
ones those arms use, so the numbers compare.

usage: pypy3 etc/py256.py f.csv        (FORCE=1 to redo, REPS=20)
       TAB=../tab  CACHE=./cache  CAP=256  WHO=py256
"""
import os, sys, time, random
Here = os.path.dirname(os.path.abspath(__file__))
Dev  = os.path.dirname(Here)
sys.path.insert(0, Here)
sys.path.insert(0, os.getenv("TAB", os.path.join(os.path.dirname(Dev), "tab")))
import min as M
import tab2 as m
from score import Acc, Auc, macro, aucposts

Cache = os.path.expanduser(os.getenv("CACHE", os.path.join(Dev, "cache")))
Reps  = int(os.getenv("REPS", 20))
Who   = os.getenv("WHO", "py256")
if os.getenv("CAP"): m.the.cap = int(os.environ["CAP"])

def home(f):
  "Where this data set's scores live, mirroring moot's tree."
  return f"{Cache}/{f.split('moot/')[-1][:-4]}"

def pair(rows, s):
  "Rep S's two halves of ROWS, from the seed alone."
  M.the.Seed = 1234567891 + s
  rows = M.shuffle(rows[:])
  n    = int(.8 * len(rows))
  return rows[:n], rows[n:]

def main(file):
  out, aout = f"{home(file)}/{Who}.csv", f"{home(file)}/{Who}auc.csv"
  if (os.path.exists(out) and os.path.exists(aout)
      and not os.getenv("FORCE")): print(out); return
  data = m.Tab(file)
  k    = data.klass
  # As lgbm.py's klassOf: a `!` column that is not discrete is not a
  # klass, and a forest of 30 cannot name a thousand of them.
  if k is None or (isinstance(k, m.Num) and
                   len({r.raw[k.at] for r in data.rows}) > 30):
    print(f"{file}: no discrete ! column, skipped", file=sys.stderr); return
  # The shuffle must walk the same list the other arms walked, or rep
  # s is a different split: same rows, same order, as min.py reads.
  if len(M.Tbl(file).rows) != len(data.rows):
    print(f"{file}: tab2 and min.py disagree on the rows, skipped",
          file=sys.stderr); return
  os.makedirs(home(file), exist_ok=True)
  acc, auc = [], []
  for s in range(1, Reps + 1):
    tr, te = pair(data.rows, s)
    random.seed(1234567891 + s)        # the forest's own draws
    t0    = time.time()
    f     = m.Forest(data.clone(tr))
    want  = [r.raw[k.at] for r in te]
    got   = [f.guess(r) for r in te]
    posts = [f.posts(r) for r in te]
    secs  = time.time() - t0
    acc.append(f"{s},{secs:.4f},{macro(want, got)}")
    auc.append(f"{s},{secs:.4f},{aucposts(want, posts)}")
  for name, head, lines in ((out, Acc, acc), (aout, Auc, auc)):
    with open(name, "w") as h:
      h.write("rep,secs," + head + "\n" + "\n".join(lines) + "\n")
  print(out)

main(sys.argv[1])
