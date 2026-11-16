#!/usr/bin/env pypy3
"""pyreg.py: tab2.py's regression forest at several row budgets.

What it guesses is lgbm.py's `goal`, so the arms compare:

    moot/regression, one numeric goal   that column, tab.y[0], raw
    anything else (moot/optimize)       ydist: distance to heaven
                                        over every goal, 0 is best

ydist is taken off the WHOLE table's goal columns, as lgbm.py and
nn.py take it, and tab2.py's formula is min.py's to the letter -- so a
row's ydist here is the number those arms were scored on.

Seven arms, all tab2.py's own trees, written like any other arm:

    pyall         Forest(train, y=...): every row, 30 bootstraps
    pycap<n>      each of the 30 trees draws its OWN n rows from train
    pyfix<n>      n rows are drawn ONCE; the 30 trees bootstrap those

`pycap` is a cheaper forest: thirty trees may read thirty times n rows
between them.  `pyfix` is a smaller budget: n labels are all there is,
so its table -- bins and all -- is built from the sample alone.

A split is a seed, not a file: min.py's shuffle is tab.lua's, so rep s
tests on the rows rep s tested on for every other arm.  `rank` and
`win` are lgbm.py's, copied, so they mean what they mean there.

usage: pypy3 etc/pyreg.py f.csv   (REPS=20, CAPS=50,100,250, FORCE=1)
       ARMS=pyfix100 pypy3 etc/pyreg.py f.csv      just those arms
       writes <cache>/<kind>/<set>/{pyall,pycap<n>,pyfix<n>}.csv
"""
import os, sys, time, math, random
Here = os.path.dirname(os.path.abspath(__file__))
Dev  = os.path.dirname(Here)
sys.path.insert(0, Here)
sys.path.insert(0, os.getenv("TAB", os.path.join(os.path.dirname(Dev), "tab")))
import min as M
import tab2 as m

Cache = os.path.expanduser(os.getenv("CACHE", os.path.join(Dev, "cache")))
Reps  = int(os.getenv("REPS", 20))
Caps  = [int(c) for c in os.getenv("CAPS", "50,100,250").split(",")]
# tab2.py now caps a regression tree at the.few rows by default.  The
# arms here say their own budgets -- `pyall` means every row -- so
# that default is switched off and each arm draws what its name says.
m.the.few = 0

def home(f): return f"{Cache}/{f.split('moot/')[-1][:-4]}"

def rank(want, got, check=5):
  "Label its best CHECK guesses: where does the best of those sit?"
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:check])
  ys    = sorted(want)
  for n, v in enumerate(ys):
    if v == best: return 100 * n / max(1, len(ys) - 1)
  return 100

def win(want, got, check=5):
  "How much of the gap it closed: 100 = the best row, 0 = an average one."
  order = sorted(range(len(got)), key=lambda j: got[j])
  best  = min(want[j] for j in order[:check])
  lo, mu = min(want), sum(want) / len(want)
  if mu == lo: return 100
  return int(math.floor(100 * (1 - (best - lo) / (mu - lo))))

def own(train, n, y):
  "A forest on TRAIN whose every tree draws its own N rows."
  f = m.Forest(train, rounds=1, y=y)              # for y, Y and tab
  c = max(1, math.floor(math.sqrt(len(train.x))))
  f.all = []
  for _ in range(m.the.rounds):
    rs = random.choices(train.rows, k=min(n, len(train.rows)))
    f.all.append(m.Tree(train, rs, [f.y(r) for r in rs], f.Y, c))
  return f

def main(file):
  arms = ["pyall"] + [f"{p}{c}" for c in Caps for p in ("pycap", "pyfix")]
  if os.getenv("ARMS"): arms = os.environ["ARMS"].split(",")
  outs = {w: f"{home(file)}/{w}.csv" for w in arms}
  if all(os.path.exists(f) for f in outs.values()) and not os.getenv("FORCE"):
    print(next(iter(outs.values()))); return
  data = m.Tab(file)
  if not data.y or not all(isinstance(c, m.Num) for c in data.y):
    print(f"{file}: wants numeric goals, skipped", file=sys.stderr); return
  if len(M.Tbl(file).rows) != len(data.rows):
    print(f"{file}: tab2 and min.py disagree on the rows, skipped",
          file=sys.stderr); return
  # lgbm.py's rule, to the letter: one goal on a regression set is
  # scored raw; everything else is ydist over the whole table's goals.
  one = "/regression/" in file and len(data.y) == 1
  at  = data.y[0].at
  mu  = data.y[0].mid()
  def want1(r):
    if not one: return data.ydist(r)
    return mu if r.raw[at] == "?" else float(r.raw[at])
  # What a forest on table T is told to guess: T's own goal column,
  # or the whole table's ydist (a function, so tab2 reads it as a
  # number whatever T is).
  target = (lambda t: t.y[0]) if one else (lambda t: data.ydist)
  os.makedirs(home(file), exist_ok=True)
  lines = {w: [] for w in arms}
  for s in range(1, Reps + 1):
    M.the.Seed = 1234567891 + s
    rows = M.shuffle(data.rows[:])
    n    = int(.8 * len(rows))
    tr, te = rows[:n], rows[n:]
    random.seed(1234567891 + s)
    train = data.clone(tr) if any(not w.startswith("pyfix") for w in arms) \
            else None
    want  = [want1(r) for r in te]
    def score(w, make):
      if w not in arms: return
      t0  = time.time()
      f   = make()
      got = [f.guess(r) for r in te]
      secs = time.time() - t0
      mae = sum(abs(a - b) for a, b in zip(want, got)) / len(want)
      lines[w].append(f"{s},{secs:.4f},{rank(want, got):.3f},"
                      f"{win(want, got)},{mae:.6g}")
    score("pyall", lambda: m.Forest(train, y=target(train)))
    for c in sorted({int(w[5:]) for w in arms if w[:5] in ("pycap", "pyfix")}):
      score(f"pycap{c}", lambda: own(train, c, target(train)))
      def few(c=c):
        sub = data.clone(random.sample(tr, min(c, len(tr))))
        return m.Forest(sub, y=target(sub))
      score(f"pyfix{c}", few)
  for w in arms:
    with open(outs[w], "w") as h:
      h.write("rep,secs,rank,win,mae\n" + "\n".join(lines[w]) + "\n")
  print(next(iter(outs.values())))

main(sys.argv[1])
