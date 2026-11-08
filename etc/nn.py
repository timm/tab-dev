#!/usr/bin/env python3
"""nn.py: a tabular foundation model, over tab-eg.lua's splits.

Same contract as lgbm.py: a split is a seed, not a file, so this
sees the rows the lua learners saw.  The model gets the whole 80%
that rmeans declines to label.

usage: python3 ,/nn.py tabicl f.csv   (writes <cache>/<set>/tabicl.csv)
       python3 ,/nn.py tabpfn f.csv
"""
import os, sys, time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import min as M
from score import Acc, Auc, aucs, macro  # one auc for every arm, so they compare

Cache = os.path.expanduser(os.getenv("CACHE", "~/tmp/cache"))
Reps  = int(os.getenv("REPS", 20))
Check = 5
Dev   = os.getenv("NN_DEVICE", "cpu")
Cap   = int(os.getenv("CAP", 950_000))    # CELLS, not rows: the
# model embeds every one.  mnist_1 is 10k rows -- under any sane row
# cap -- but 785 columns wide, and four of those at once filled 32GB
# of swap.  Measured: all_players, at 1.01M cells, peaked at 8.3GB
# -- roughly 8KB per cell.  So 1M is about 8GB for one worker, and
# two of those is already a third of a 24GB machine.  2M was tried
# and is not safe here.  tab, for the same work, peaks at 2.9MB.
# 950k, not 1M, because two workers have to fit at once.  950k and
# not 900k so that binary_config/billing10k, at 910,000, stays in: it
# had already run, and a cap that declines a set we hold is a cap
# that lies.
Rows  = int(os.getenv("ROWS", 15_000))    # and a second cap, on rows
# alone, because the two costs do not have the same shape.  Memory is
# linear in cells; time is quadratic in rows and blind to width.
# Measured 35 min at 10k rows and 130 min at 20k, so t = 3.5e-7 r^2
# minutes.  regression/2dplanes is 40,768 rows in 11 columns -- 448k
# cells, well inside the cell cap -- and wanted 9.7 hours on its own.
# A cells cap cannot see that set coming.  At 15k rows the worst set
# costs 1.3 hours and the optimize corpus costs 13, against 20 hours
# and five more sets at 20k: the five are not worth the seven hours.

def arms(who, klass):
  "WHO's classifier or regressor, as a fresh model."
  if who == "tabicl":
    from tabicl import TabICLClassifier, TabICLRegressor
    m = TabICLClassifier if klass else TabICLRegressor
  else:
    from tabpfn import TabPFNClassifier, TabPFNRegressor
    m = TabPFNClassifier if klass else TabPFNRegressor
  try:    return m(device=Dev, random_state=0)
  except TypeError: return m(device=Dev)

def home(f):
  "Where this data set's scores live, mirroring moot's tree."
  return f"{Cache}/{f.split('moot/')[-1][:-4]}"

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
  "Numbers in, label out.  A klass is a string: models return those."
  X, y = [], []
  for r in t.rows:
    X.append([float("nan")                          if r[c.at] == "?" else
              i.setdefault((c.at, r[c.at]), len(i)) if type(c) is M.SYM else
              float(r[c.at])                        for c in t.cols.x])
    y.append(str(r[klass.at]) if klass else goal(t, file)(r))
  return X, y

def rank(want, got):
  "Label its best CHECK guesses: where does the best of those sit?"
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:Check])
  ys    = sorted(want)
  for n, v in enumerate(ys):
    if v == best: return 100 * n / max(1, len(ys) - 1)
  return 100

def win(want, got):
  """How much of the gap it closed: 100 = the best row, 0 = an average
  one.  `rank` counts how many rows beat us and saturates where many
  rows sit a hair apart; this counts the y given up instead.  Must
  match `gap` in tab-eg.lua and `win` in lgbm.py, floor included, or
  the arms do not compare."""
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:Check])
  lo, mu = min(want), sum(want) / len(want)
  if mu == lo: return 100
  return int(math.floor(100 * (1 - (best - lo) / (mu - lo))))

def klassOf(t, file):
  "Classify sets guess the last ! column, if it is discrete."
  if "/classify/" not in file: return None
  c = next((c for c in reversed(t.cols.y) if c.txt.endswith("!")), None)
  if c is None or type(c) is M.SYM: return c
  return c if len({r[c.at] for r in t.rows}) <= 30 else None

def main(who, file):
  "Score WHO on every rep, unless that was already done."
  # AUC=1 writes <who>auc.csv and leaves <who>.csv alone: the two are
  # different questions of the same model, not two versions of one.
  auc = bool(os.getenv("AUC"))
  out = f"{home(file)}/{who}{'auc' if auc else ''}.csv"
  if os.path.exists(out) and not os.getenv("FORCE"): print(out); return
  os.makedirs(home(file), exist_ok=True)
  t     = M.Tbl(file)
  wide  = len(t.cols.x) + len(t.cols.y)
  if len(t.rows) * wide > Cap:    # it holds the training set in memory
    print(f"{file}: {len(t.rows)}x{wide} = {len(t.rows)*wide:,} cells"
          f" over CAP={Cap:,}, skipped", file=sys.stderr); return
  if len(t.rows) > Rows:          # and it is quadratic in the rows
    print(f"{file}: {len(t.rows)} rows over ROWS={Rows:,}, skipped",
          file=sys.stderr); return
  klass = klassOf(t, file)
  if "/classify/" in file and not klass:
    print(f"{file}: no discrete ! column, skipped", file=sys.stderr); return
  if auc and not klass:
    print(f"{file}: AUC wants a klass, skipped", file=sys.stderr); return
  model = arms(who, klass)     # once: rep 1 pays the checkpoint load
  lines = []
  for s in range(1, Reps + 1):
    tr, te = pair(t, s)
    i      = {}
    X1, y1 = xy(tr, i, klass, file)
    X2, y2 = xy(te, i, klass, file)
    t0     = time.time()
    model.fit(X1, y1)
    if auc:
      line = aucs(model, X2, y2)
    else:
      got  = list(model.predict(X2))
      line = (macro(y2, got) if klass else
              f"{rank(y2, got):.3f},{win(y2, got)},"
              # %.6g, not %.3f: three decimals rounded a small mae to
              # the same string on every set and hid a stale cache
              # once already.  Every other arm prints this way.
              f"{sum(abs(a-b) for a, b in zip(y2, got)) / len(y2):.6g}")
    secs   = time.time() - t0
    lines.append(f"{s},{secs:.4f},{line}")
  with open(out, "w") as f:
    f.write("rep,secs," + (Auc if auc else
                           Acc if klass else "rank,win,mae") + "\n")
    f.write("\n".join(lines) + "\n")
  print(out)

main(sys.argv[1], sys.argv[2])
