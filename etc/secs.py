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
import os, sys, time, random, subprocess

Here  = os.path.dirname(os.path.abspath(__file__))
Dev   = os.path.dirname(Here)
Tab   = os.getenv("TAB", os.path.join(os.path.dirname(Dev), "tab"))
Moot  = os.path.expanduser(os.getenv("MOOT", "~/gits/moot"))
NN    = os.path.expanduser(os.getenv("NN", "~/tmp/nnenv/bin/python"))
Out   = os.getenv("SECS", os.path.join(Dev, "cache", "secs.csv"))
Cap, Grace, Budget, Fits = 120, 60, 20, 5
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

def roles(names):
  "x columns and the klass column: the last one ending in `!`."
  ks = [j for j, n in enumerate(names) if n.endswith("!")]
  xs = [j for j, n in enumerate(names) if n and n[-1] not in "X-+!"]
  return xs, (ks[-1] if ks else None)

def shape(file):
  "rows, x columns, klasses -- or None if there is nothing to classify."
  names, rows = load(file)
  xs, k = roles(names)
  if k is None or not xs: return None
  return len(rows), len(xs), len({r[k] for r in rows if r[k] != "?"})

def xy(file):
  "Numbers in, label out, split 80:20.  Syms become codes, `?` nan."
  names, rows = load(file)
  xs, k = roles(names)
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
  y = [r[k] for r in rows]
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
  from lightgbm import LGBMClassifier
  X1, y1, X2, _ = xy(file)
  X1, X2 = np.array(X1), np.array(X2)
  def once():
    LGBMClassifier(verbose=-1, n_jobs=1).fit(X1, y1).predict(X2)
  fits(once, budget, most)

def tabicl(file, budget, most, threads="1"):
  "THREADS=0 is as shipped; anything else is that many."
  import inspect, numpy as np, torch
  if int(threads): torch.set_num_threads(int(threads))
  from tabicl import TabICLClassifier
  X1, y1, X2, _ = xy(file)
  X1, X2 = np.array(X1), np.array(X2)
  kw = {"device": "cpu", "random_state": 0}
  if int(threads) and "n_jobs" in inspect.signature(
       TabICLClassifier.__init__).parameters: kw["n_jobs"] = int(threads)
  model = TabICLClassifier(**kw)
  # The checkpoint loads inside the first fit, and that is a cost of
  # starting python, not of learning: soybean's first fit was 19.8s
  # against 7.5s for every one after.  So load it on a fit too small
  # to matter, untimed, the way pypy is given its two warm fits.
  try: model.fit(X1[:64], y1[:64]).predict(X2[:2])
  except Exception: pass
  fits(lambda: model.fit(X1, y1).predict(X2), budget, most)

def tab2(file, budget, most, bins="7", cap="0"):
  """tab2.py's forest, under whatever interpreter ran this.  CAP is
  always set, never left to tab2's default, so an arm measured before
  tab2 grew a cap still means what it meant: no cap."""
  sys.path.insert(0, Tab)
  import tab2 as m
  m.the.bins, m.the.cap = int(bins), int(cap)
  random.seed(Seed)
  data = m.Tab(file)
  rows = data.rows[:]; random.shuffle(rows)
  n = int(.8 * len(rows))
  train, test = data.clone(rows[:n]), rows[n:]
  def once():
    f = m.Forest(train)
    for r in test: f.guess(r)
  fits(once, budget, most)

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

def pick(n):
  "N classify sets: five bands of rows, spread over klasses in each."
  all_ = []
  for f in sorted(os.listdir(f"{Moot}/classify")):
    if f.endswith(".csv") and f[:-4] not in Skip:
      s = shape(f"{Moot}/classify/{f}")
      if s and s[2] > 1: all_.append((s[0], s[2], s[1], f[:-4]))
  all_.sort()
  out, per = [], max(1, n // 5)
  for b in range(5):
    band = sorted(all_[b * len(all_) // 5:(b + 1) * len(all_) // 5],
                  key=lambda s: (s[1], s[0]))
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

def run(n):
  done = set()
  if os.path.exists(Out):
    for s in list(open(Out))[1:]: done.add(tuple(s.split(",")[:2]))
  else:
    os.makedirs(os.path.dirname(Out), exist_ok=True)
    with open(Out, "w") as h:
      h.write("set,arm,rows,x,klasses,status,secs,cpu,fits\n")
  for rows, k, x, name in pick(n):
    for arm in Arms:
      if (name, arm[0]) in done: continue
      t = time.time()
      status, w, c, fs = one(arm, f"{Moot}/classify/{name}.csv", rows, x)
      with open(Out, "a") as h:
        h.write(f"{name},{arm[0]},{rows},{x},{k},{status},{w},{c},{fs}\n")
      print(f"{name:28} {arm[0]:8} {status:8} {w:>10}  "
            f"({time.time() - t:5.1f}s)", flush=True)

if __name__ == "__main__":
  a = sys.argv[1:]
  if   a and a[0] == "run":  run(int(a[1]) if len(a) > 1 else 30)
  elif a and a[0] == "sets":
    for s in pick(int(a[1]) if len(a) > 1 else 30): print(*s)
  elif a and a[0] in ("lgbm", "tabicl", "tab2"):
    globals()[a[0]](a[1], float(a[2]), int(a[3]), *a[4:6])
  else: print(__doc__)
