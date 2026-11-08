#!/usr/bin/env python3
"""lgbm.py: LightGBM, over min-eg.lua's splits, scored its way.

A split is a seed, not a file: min.py's `rint` and `shuffle` are
the ones in min.lua, so this sees the rows the lua learners saw.

usage: python3 ,/lgbm.py f.csv        (writes <cache>/<set>/lgbm.csv)
"""
import os, sys, time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import min as M
from score import Acc, Auc, aucs, macro
from lightgbm import LGBMClassifier, LGBMRegressor

Cache = os.path.expanduser(os.getenv("CACHE", "~/tmp/cache"))
# REPS: an override for timing runs, mirroring forest-eg.lua, so
# both sides of a comparison can be asked for the same count.
Reps  = int(os.getenv("REPS") or 20)

def home(f):
  "Where this data set's scores live, mirroring moot's tree."
  m = f.split("moot/")[-1]
  return f"{Cache}/{m[:-4]}"

def pair(t, s):
  "Rep S's two halves of T, from the seed alone."
  M.the.Seed = 1234567891 + s
  rows = M.shuffle(t.rows[:])
  n    = int(.8 * len(rows))
  return M.clone(t, rows[:n]), M.clone(t, rows[n:])

def goal(t, file):
  "Regression: that one column, in its own units.  Else: ydist."
  c = t.cols.y[0] if "/regression/" in file and len(t.cols.y) == 1 else None
  if c is None or type(c) is not M.NUM:
    return lambda r: M.ydist(t, r)   # 0 is best whatever col.w says, and
  return lambda r: c.mu if r[c.at] == "?" else float(r[c.at])  # mae then
                                     # compares across sets

def xy(t, i, klass, file):
  "Numbers in, label out.  Syms map through I, shared by the splits."
  X, y = [], []
  for r in t.rows:
    X.append([float("nan")                       if r[c.at] == "?" else
              i.setdefault((c.at, r[c.at]), len(i)) if type(c) is M.SYM else
              float(r[c.at])                     for c in t.cols.x])
    y.append(str(r[klass.at]) if klass else goal(t, file)(r))
  return X, y

def rank(want, got, check=5):
  "Label its best CHECK guesses: where does the best of those sit?"
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:check])
  ys    = sorted(want)
  for n, v in enumerate(ys):
    if v == best: return 100 * n / max(1, len(ys) - 1)
  return 100

def win(want, got, check=5):
  """How much of the gap it closed: 100 = the best row, 0 = an average
  one.  `rank` counts how many rows beat us and saturates where many
  rows sit a hair apart; this counts the y given up instead.  Must
  match `gap` in tab-eg.lua, floor included, or the arms do not
  compare."""
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:check])
  lo, mu = min(want), sum(want) / len(want)
  if mu == lo: return 100
  return int(math.floor(100 * (1 - (best - lo) / (mu - lo))))

def klassOf(t, file):
  "Classify sets guess the last ! column, if it is discrete."
  if "/classify/" not in file: return None
  c = next((c for c in reversed(t.cols.y) if c.txt.endswith("!")), None)
  if c is None or type(c) is M.SYM: return c
  return c if len({r[c.at] for r in t.rows}) <= 30 else None

Jobs = ({"n_jobs": int(os.environ["LGBM_JOBS"])}
        if os.getenv("LGBM_JOBS") else {})

def main(file):
  "Score LightGBM on every rep, unless that was already done."
  # LABELS=n trains on the FIRST n training rows instead of all of
  # them.  `pair` here and `pair` in tab.lua share a seed and a
  # Park-Miller shuffle, so those n rows are the very same rows tab's
  # `head1(tr.rows, the.budget - the.check)` hands its own learners:
  # the arms differ by learner alone, not by which labels they saw.
  lab = int(os.getenv("LABELS", 0))
  who = ("lgbmauc" if os.getenv("AUC") else "lgbm") + (f"{lab}" if lab else "")
  out = f"{home(file)}/{who}.csv"
  if os.path.exists(out) and not os.getenv("FORCE"): print(out); return
  os.makedirs(home(file), exist_ok=True)
  t     = M.Tbl(file)
  klass = klassOf(t, file)
  if "/classify/" in file and not klass:
    print(f"{file}: no discrete ! column, skipped", file=sys.stderr); return
  lines = []
  for s in range(1, Reps + 1):
    tr, te = pair(t, s)
    if lab: tr = M.clone(t, tr.rows[:lab])
    i      = {}
    X1, y1 = xy(tr, i, klass, file)
    X2, y2 = xy(te, i, klass, file)
    t0     = time.time()
    # n_jobs: LightGBM defaults to every core, while tab is single
    # threaded.  A timing run must say which it wants -- LGBM_JOBS=1
    # for the per-core claim, unset for "as shipped".  Scores do not
    # depend on it, only seconds do.
    model  = (LGBMClassifier if klass else LGBMRegressor)(
               verbose=-1, **Jobs)
    model.fit(X1, y1)
    if who == "lgbmauc":
      line = aucs(model, X2, y2)
    else:
      got  = list(model.predict(X2))
      line = (macro(y2, got) if klass else
              f"{rank(y2, got):.3f},{win(y2, got)},"
              f"{sum(abs(a-b) for a,b in zip(y2,got))/len(y2):.6g}")
    secs   = time.time() - t0
    lines.append(f"{s},{secs:.4f},{line}")
  with open(out, "w") as f:
    f.write("rep,secs," + (Auc if who == "lgbmauc" else
                           Acc if klass else "rank,win,mae") + "\n")
    f.write("\n".join(lines) + "\n")
  print(out)

main(sys.argv[1])
