#!/usr/bin/env python3
"""secs.py: what one fit and predict costs, measured one way for every arm.

This replaces the `secs` column that rawnum.png drew (retired
2026-11-14, see CLAUDE.md).  That column stacked three defects, all
flattering tab: a cpu clock for the lua arms against a wall clock for
the python ones, one thread against ten, and an `xargs -P 8` harness
that cost the threaded arm more than the others.  Here:

  - every arm is timed on a WALL clock, and prints its cpu time beside
    it, so cpu/wall near 1.0 is the proof it ran on one thread;
  - every arm is told to use one thread (`tabicl` also runs as shipped,
    and is named apart);
  - a set's arms run back to back, serially, nothing in parallel;
  - the same work is timed for each: fit on 80%, predict the other 20%;
  - nothing here reads or writes the score caches.

usage: python3 etc/secs.py run [n]       n sets, stratified (default 30)
       python3 etc/secs.py sets [n]      just name them
       python3 etc/secs.py run 30 regression    -> cache/secsreg.csv
       <interp> etc/secs.py <arm> f.csv budget maxfits [opt]   one arm

A worker prints `fit <wall> <cpu>` per completed fit and stops
repeating once another fit would pass BUDGET seconds.  The driver
kills a worker at CAP seconds past GRACE, the same for every arm, and
writes what it has: a set an arm could not finish is recorded as
`capped`, not dropped -- dropping it would keep only the sets the dear
arm finds cheap.

The seconds reported are the min of the fits after the first two
(pypy needs two to warm; the others lose nothing by it), or the last
fit when there was no room for three.
"""
import os, sys, time, math, glob, random, subprocess

Here  = os.path.dirname(os.path.abspath(__file__))
Dev   = os.path.dirname(Here)
Tab   = os.getenv("TAB", os.path.join(os.path.dirname(Dev), "tab"))
Moot  = os.path.expanduser(os.getenv("MOOT", "~/gits/moot"))
NN    = os.path.expanduser(os.getenv("NN", "~/tmp/nnenv/bin/python"))
Out   = os.getenv("SECS", os.path.join(Dev, "cache", "secs.csv"))
Cap, Grace, Budget, Fits = int(os.getenv("CAP", 120)), 60, 20, 5
Skip  = ("COMPAS53", "mnist_1")      # as ,/run: 85% of a tree arm alone
Cells, Rows = 950_000, 15_000        # nn.py's memory and time guards
Seed  = 1234567891 + 1

# ---- data, for the driver and the two python arms ---------------------
def load(file):
  "names, rows of cells; tab's header rules, none of its code."
  with open(file, encoding="utf-8-sig") as f:
    rows = [[c.strip() for c in s.split(",")]
            for s in (line.strip() for line in f) if s and s[0] != "#"]
  names = rows[0]
  return names, [r for r in rows[1:] if len(r) == len(names)]

def reg(file):
  "Is FILE's target a number?  Its place in moot says so."
  return "/regression/" in file or "/optimize/" in file

def ydists(names, rows):
  """Each row's distance to heaven over the goal columns -- tab's
  ydist, off the whole table: logistic of z per goal, 0 or 1 as the
  goal is to shrink or grow, root mean square over the goals."""
  gs = {}
  for j, n in enumerate(names):
    if n and n[-1] in "+-":
      v  = [float(r[j]) for r in rows if r[j] != "?"]
      mu = sum(v) / len(v)
      sd = (sum((x - mu) ** 2 for x in v) / max(1, len(v) - 1)) ** .5
      gs[j] = (mu, sd, 0 if n[-1] == "-" else 1)
  def one(r):
    d = 0
    for j, (mu, sd, w) in gs.items():
      v = mu if r[j] == "?" else float(r[j])
      z = max(-3, min(3, (v - mu) / (sd + 1e-32)))
      d += abs(1 / (1 + math.exp(-1.7 * z)) - w) ** 2
    return (d / len(gs)) ** .5
  return [one(r) for r in rows]

def roles(names, num=False):
  """x columns and the target: the last `!` column, a klass -- or, for
  NUM, the last goal column of any kind, a number."""
  ks = [j for j, n in enumerate(names)
        if n and n[-1] in ("+-!" if num else "!")]
  xs = [j for j, n in enumerate(names) if n and n[-1] not in "X-+!"]
  return xs, (ks[-1] if ks else None)

def shape(file):
  "rows, x columns, klasses -- or None if there is nothing to classify."
  names, rows = load(file)
  xs, k = roles(names, reg(file))
  if k is None or not xs: return None
  if reg(file): return len(rows), len(xs), 1      # no klasses to count
  return len(rows), len(xs), len({r[k] for r in rows if r[k] != "?"})

def xy(file):
  "Numbers in, label out, split 80:20.  Syms become codes, `?` nan."
  names, rows = load(file)
  xs, k = roles(names, reg(file))
  rows  = [r for r in rows if r[k] != "?"]
  random.Random(Seed).shuffle(rows)
  code = {}
  def cell(j, v):
    if v == "?": return float("nan")
    if names[j][0].isupper():
      try: return float(v)
      except ValueError: return float("nan")
    return float(code.setdefault((j, v), len(code)))
  X = [[cell(j, r[j]) for j in xs] for r in rows]
  y = (ydists(names, rows) if "/optimize/" in file else
       [float(r[k]) if reg(file) else r[k] for r in rows])
  n = int(.8 * len(rows))
  return X[:n], y[:n], X[n:], y[n:]

# ---- workers -----------------------------------------------------------
def fits(once, budget, most):
  "Time ONCE until another would pass BUDGET, telling the driver each."
  began, last = time.perf_counter(), 0
  for k in range(most):
    if k and time.perf_counter() - began + last > budget: break
    w, c = time.perf_counter(), time.process_time()
    once()
    last = time.perf_counter() - w
    print(f"fit {last:.6f} {time.process_time() - c:.6f}", flush=True)

def lgbm(file, budget, most, _=None):
  import numpy as np
  from lightgbm import LGBMClassifier, LGBMRegressor
  X1, y1, X2, _ = xy(file)
  X1, X2 = np.array(X1), np.array(X2)
  Model = LGBMRegressor if reg(file) else LGBMClassifier
  def once():
    Model(verbose=-1, n_jobs=1).fit(X1, y1).predict(X2)
  fits(once, budget, most)

def tabicl(file, budget, most, threads="1"):
  "THREADS=0 is as shipped; anything else is that many."
  import inspect, numpy as np, torch
  if int(threads): torch.set_num_threads(int(threads))
  from tabicl import TabICLClassifier, TabICLRegressor
  X1, y1, X2, _ = xy(file)
  X1, X2 = np.array(X1), np.array(X2)
  Model = TabICLRegressor if reg(file) else TabICLClassifier
  kw = {"device": "cpu", "random_state": 0}
  if int(threads) and "n_jobs" in inspect.signature(
       Model.__init__).parameters: kw["n_jobs"] = int(threads)
  model = Model(**kw)
  # The checkpoint loads inside the first fit, and that is a cost of
  # starting python, not of learning: soybean's first fit was 19.8s
  # against 7.5s for every one after.  So load it on a fit too small
  # to matter, untimed, the way pypy is given its two warm fits.
  try: model.fit(X1[:64], y1[:64]).predict(X2[:2])
  except Exception: pass
  fits(lambda: model.fit(X1, y1).predict(X2), budget, most)

def tab2(file, budget, most, bins="7", cap="0", few="0", own="0"):
  """tab2.py's forest, under whatever interpreter ran this.  CAP is
  always set, never left to tab2's default, so an arm measured before
  tab2 grew a cap still means what it meant: no cap.

  On a regression set the forest guesses y[0], and FEW is its whole
  label budget: each fit draws FEW rows, builds its table from those
  alone, and grows all its trees on them.  The draw and the table are
  inside the clock -- they are the work this arm does instead of
  reading every row."""
  sys.path.insert(0, Tab)
  import tab2 as m
  m.the.bins, m.the.cap = int(bins), int(cap)
  # OWN is tab2's own row budget, the.few: each tree draws that many
  # rows for itself (0: all).  FEW, below, is the other style -- one
  # sample of that many rows, shared by every tree.  Never both.
  m.the.few = int(own)
  random.seed(Seed)
  data = m.Tab(file)
  rows = data.rows[:]; random.shuffle(rows)
  n = int(.8 * len(rows))
  train, test = data.clone(rows[:n]), rows[n:]
  def once():
    f = m.Forest(train)
    for r in test: f.guess(r)
  def once_num():
    t = train
    if int(few):
      t = data.clone(random.sample(rows[:n], min(int(few), n)))
    f = m.Forest(t, y=data.ydist if "/optimize/" in file else t.y[0])
    for r in test: f.guess(r)
  fits(once_num if reg(file) else once, budget, most)

# ---- driver ------------------------------------------------------------
One  = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
Self = os.path.abspath(__file__)
Arms = [  # name, argv before the file, argv after the counts, env, big?
  ("luajit",  ["luajit", os.path.join(Here, "secs.lua")], [], {}, 0),
  ("lgbm",    [NN, Self, "lgbm"],     [],     One, 0),
  ("tab2",    ["pypy3", Self, "tab2"], ["7", "0"],  {},  0),
  ("tab2b50", ["pypy3", Self, "tab2"], ["50", "0"], {},  0),
  # At most 256 rows of any klass per tree, tab2's default.  The
  # uncapped arms above pass cap=0 so they stay what they were.
  ("tab2c256", ["pypy3", Self, "tab2"], ["7", "256"], {}, 0),
  ("tabicl1", [NN, Self, "tabicl"],   ["1"],  One, 1),
  ("tabicl",  [NN, Self, "tabicl"],   ["0"],  {},  1)]
# Regression: the three treatments regmae.png draws.  `tab2f100` is 30
# trees on one shared sample of 100 rows.
RegArms = [
  ("lgbm",     [NN, Self, "lgbm"],      [],                One, 0),
  ("tab2f100", ["pypy3", Self, "tab2"], ["7", "0", "100"], {},  0),
  # tab2 as it ships for a numeric target: 30 trees, each drawing its
  # own 200 rows.  Every training row is binned first, inside the
  # clock, because any of them may be drawn.
  ("tab2o200", ["pypy3", Self, "tab2"], ["7", "0", "0", "200"], {}, 0),
  ("tabicl1",  [NN, Self, "tabicl"],    ["1"],             One, 1)]

def pick(n, kind="classify"):
  """N sets of KIND: five bands of rows, spread over klasses in each
  (or, for regression, where every set has one "klass", over columns)."""
  all_ = []
  if kind == "optimize":
    # One level deeper, so a set is named group/name -- which is also
    # its path under moot/optimize.  Only sets optmae.png draws: both
    # other arms scored, and TabICL's file not on the stale list.
    stale = {l.strip() for l in open(f"{Dev}/STALE-tabicl.txt")
             if l.strip() and l[0] != "#"}
    for p in sorted(glob.glob(f"{Moot}/optimize/*/*.csv")):
      name = p.split("/optimize/")[1][:-4]
      d = f"{Dev}/cache/optimize/{name}"
      if (os.path.exists(f"{d}/pyfix100.csv") and
          os.path.exists(f"{d}/tabicl.csv") and
          f"optimize/{name}" not in stale):
        s = shape(p)
        if s and s[0] > 0: all_.append((s[0], s[2], s[1], name))
  for f in ([] if kind == "optimize" else
            sorted(os.listdir(f"{Moot}/{kind}"))):
    if f.endswith(".csv") and f[:-4] not in Skip:
      s = shape(f"{Moot}/{kind}/{f}")
      # Regression: only sets the error chart draws, so the runtime
      # and the mae figures speak of one corpus -- and never a file
      # whose rows this loader cannot read (three come back empty).
      if kind == "regression":
        if s and s[0] > 0 and os.path.exists(
             f"{Dev}/cache/regression/{f[:-4]}/pyfix100.csv"):
          all_.append((s[0], s[2], s[1], f[:-4]))
      elif s and s[2] > 1: all_.append((s[0], s[2], s[1], f[:-4]))
  all_.sort()
  out, per = [], max(1, n // 5)
  for b in range(5):
    band = sorted(all_[b * len(all_) // 5:(b + 1) * len(all_) // 5],
                  key=(lambda s: (s[2], s[0])) if kind != "classify"
                  else (lambda s: (s[1], s[0])))   # as it always was
    for j in range(min(per, len(band))):
      out.append(band[round(j * (len(band) - 1) / max(1, per - 1))])
  return sorted(set(out))

def one(arm, file, rows, x):
  "Run ARM on FILE; (status, secs, cpu, fits)."
  name, pre, post, env, big = arm
  if big and (rows > Rows or rows * (x + 1) > Cells):
    return "declined", "", "", ""
  p = subprocess.Popen(pre + [file, str(Budget), str(Fits)] + post,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, cwd=Dev,
                       env={**os.environ, "TAB": Tab, **env})
  try: out, err = p.communicate(timeout=Cap + Grace); late = False
  except subprocess.TimeoutExpired:
    p.kill(); out, err = p.communicate(); late = True
  got = [s.split()[1:] for s in out.splitlines() if s.startswith("fit ")]
  if not got:
    if late: return "capped", "", "", ""
    sys.stderr.write(f"{name} {file}: {err.strip()[-300:]}\n")
    return "error", "", "", ""
  use = got[2:] if len(got) > 2 else got[-1:]
  w, c = min(use, key=lambda t: float(t[0]))
  return "ok", w, c, " ".join(t[0] for t in got)

def run(n, kind="classify"):
  # Regression keeps its own file: the arms differ, and a set name may
  # live in both corpora.
  Out  = globals()["Out"] if kind == "classify" else os.getenv(
           "SECSREG", os.path.join(Dev, "cache", "secsopt.csv" if
                                   kind == "optimize" else "secsreg.csv"))
  done = set()
  if os.path.exists(Out):
    for s in list(open(Out))[1:]: done.add(tuple(s.split(",")[:2]))
  else:
    os.makedirs(os.path.dirname(Out), exist_ok=True)
    with open(Out, "w") as h:
      h.write("set,arm,rows,x,klasses,status,secs,cpu,fits\n")
  for rows, k, x, name in pick(n, kind):
    for arm in (Arms if kind == "classify" else RegArms):
      if (name, arm[0]) in done: continue
      t = time.time()
      status, w, c, fs = one(arm, f"{Moot}/{kind}/{name}.csv", rows, x)
      with open(Out, "a") as h:
        h.write(f"{name},{arm[0]},{rows},{x},{k},{status},{w},{c},{fs}\n")
      print(f"{name:28} {arm[0]:8} {status:8} {w:>10}  "
            f"({time.time() - t:5.1f}s)", flush=True)

if __name__ == "__main__":
  a = sys.argv[1:]
  kind = a[2] if len(a) > 2 else "classify"
  if   a and a[0] == "run":  run(int(a[1]) if len(a) > 1 else 30, kind)
  elif a and a[0] == "sets":
    for s in pick(int(a[1]) if len(a) > 1 else 30, kind): print(*s)
  elif a and a[0] in ("lgbm", "tabicl", "tab2"):
    globals()[a[0]](a[1], float(a[2]), int(a[3]), *a[4:8])
  else: print(__doc__)
