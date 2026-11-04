#!/usr/bin/env python3
"""cc18.py: OpenML-CC18, as moot csvs.

moot's 73 classify sets are small, nominal and many-klass; CC18's 72
are large, numeric and mostly binary.  That is the point of adding
them -- the corpora disagree about what a tabular problem is, so a
result that holds on both holds wider.  19 sets overlap by name and
are skipped; this fetches the other 53 and admits them on three
checks decided on SHAPE, before any learner runs:

  klass   exactly one klass column, symbolic, at most `maxklass`
          distinct.  moot itself fails this on four sets (wine,
          spectrometer, spectf.test, spectf.train), where the `!`
          marker sits on a numeric column -- so this asserts rather
          than trusting a header.
  test    at least `mintest` test rows.  20 reps x 10 rows resolves
          0.5 accuracy points, under the 0.3-3 point deltas we are
          trying to see.
  size    rows * sqrt(cols) at most `maxcost`.  Drops the six image
          and mega-row sets (CIFAR_10, Devnagari-Script, mnist_784,
          Fashion-MNIST, numerai28.6, connect-4), which are 80% of a
          corpus run's wall clock and all of it in the baselines --
          tabicl alone wants 240 hours on those six.

Column names carry their type, as moot's do: a numeric attribute is
Capitalized (tab reads A-Z as Num, a-z as Sym) and the klass is
lowercased with a `!`, last.

usage: cc18.py [--list] [--out DIR] [NAME ...]
"""
import os, sys, json, math, re, subprocess, csv

Api     = "https://www.openml.org/api/v1/json"
Suite   = 99                      # the OpenML-CC18 study id
Out     = os.path.expanduser("~/gits/moot/classify")
Moot    = os.path.expanduser("~/gits/moot/classify")
Mintest = 10
Maxcost = 400_000                 # rows * sqrt(cols)
Maxklass= 30

def get(url):
  """Through curl, not urllib: this python has no CA bundle it can
  find, and OpenML is https only."""
  r = subprocess.run(["curl", "-sSL", "--max-time", "300", url],
                     capture_output=True)
  if r.returncode: raise IOError(r.stderr.decode()[:200])
  return r.stdout

def jget(url): return json.loads(get(url))

def norm(s): return re.sub(r"[-_. ]", "", s.lower())

def suite():
  "Every CC18 dataset: name, did, rows, cols, klasses."
  s   = jget(f"{Api}/study/{Suite}")["study"]
  ids = ",".join(s["data"]["data_id"])
  out = []
  for d in jget(f"{Api}/data/list/data_id/{ids}")["data"]["dataset"]:
    q = {x["name"]: float(x["value"]) for x in d["quality"]}
    out.append(dict(name=d["name"], did=d["did"],
                    rows=int(q.get("NumberOfInstances", 0)),
                    cols=int(q.get("NumberOfFeatures", 0)),
                    klass=int(q.get("NumberOfClasses", 0))))
  return out

# Same UCI data, different OpenML name -- verified by shape, not by
# guessing: credit-approval is 690x16, and so is moot's credit.a.
Alias = {"credit-approval": "credit.a"}

def mine():
  "What moot already holds, by normalized name."
  return ({norm(f[:-4]) for f in os.listdir(Moot) if f.endswith(".csv")}
          | {norm(k) for k in Alias})

def wanted(all, have):
  """CC18 minus moot, minus what the size check drops.  Returns the
  keepers and, beside them, every rejection and its reason -- a run
  that drops a set silently cannot be audited later."""
  keep, drop = [], []
  for d in all:
    cost = d["rows"] * math.sqrt(max(d["cols"], 1))
    if norm(d["name"]) in have:  drop.append((d, "in moot already"))
    elif cost > Maxcost:         drop.append((d, f"size {cost:,.0f} > {Maxcost:,}"))
    elif int(.2 * d["rows"]) < Mintest:
                                 drop.append((d, f"test rows {int(.2*d['rows'])} < {Mintest}"))
    else: keep.append(d)
  return keep, drop

# ---- arff ----------------------------------------------------------
def arff(txt):
  """An ARFF's attributes and rows.  Handles quoted values, `?` and
  the nominal `{a,b,c}` form; a sparse ARFF (`{3 1,7 1}` rows) is
  refused rather than read wrong."""
  names, kinds, rows, data = [], [], [], False
  for line in txt.splitlines():
    s = line.strip()
    if not s or s.startswith("%"): continue
    if not data:
      low = s.lower()
      if low.startswith("@attribute"):
        m = re.match(r"@attribute\s+('[^']*'|\"[^\"]*\"|\S+)\s+(.*)$", s, re.I)
        nm, ty = m.group(1).strip("'\""), m.group(2).strip()
        names.append(nm)
        kinds.append("num" if ty.lower() in ("numeric","real","integer")
                     else "sym")
      elif low.startswith("@data"): data = True
    else:
      if s.startswith("{"): raise ValueError("sparse arff")
      rows.append(next(csv.reader([s], skipinitialspace=True)))
  return names, kinds, rows

def klassAt(names, kinds, rows):
  """Which column is the klass.  CC18 tasks all name a target, but
  the ARFF does not say which it is, so: the last symbolic column
  with 2..Maxklass distinct values.  Checked, not assumed."""
  for at in range(len(names) - 1, -1, -1):
    if kinds[at] != "sym": continue
    vs = {r[at] for r in rows if len(r) > at and r[at] != "?"}
    if 2 <= len(vs) <= Maxklass: return at
  return None

def ider(rows, j, n):
  """Is column `j` an identifier?  A value unique to every row says
  nothing a later row can use, so moot's `X` suffix skips it.  Named
  ids are NOT caught here: `Run` in climate-model-simulation-crashes
  repeats across three studies, so only a human can call that one."""
  vs = {r[j] for r in rows if len(r) > j and r[j] != "?"}
  return n > 10 and len(vs) == n

def mootify(names, kinds, rows, at):
  "ARFF columns as moot's: Capital = Num, lower = Sym, klass last."
  n = len(rows)
  def nm(j):
    t = re.sub(r"[^A-Za-z0-9]", "_", names[j]) or f"c{j}"
    if not t[0].isalpha(): t = "c" + t
    t = t.capitalize() if kinds[j] == "num" else t.lower()
    return t + "X" if j != at and ider(rows, j, n) else t
  xs  = [j for j in range(len(names)) if j != at]
  hdr = [nm(j) for j in xs] + [nm(at) + "!"]
  out = [hdr]
  for r in rows:
    if len(r) < len(names): continue       # a truncated line is a skip
    out.append([r[j].strip() or "?" for j in xs] + [r[at].strip() or "?"])
  return out

def fetch(d, out):
  "One CC18 set, written as `out`/NAME.csv.  Returns a note."
  meta = jget(f"{Api}/data/{d['did']}")["data_set_description"]
  txt  = get(meta["url"]).decode("utf8", "replace")
  names, kinds, rows = arff(txt)
  at = klassAt(names, kinds, rows)
  if at is None: return f"no klass column in 2..{Maxklass} values"
  tbl = mootify(names, kinds, rows, at)
  if int(.2 * (len(tbl) - 1)) < Mintest:
    return f"test rows {int(.2*(len(tbl)-1))} < {Mintest} once read"
  f = os.path.join(out, d["name"].replace("/", "_") + ".csv")
  with open(f, "w", newline="") as h: csv.writer(h).writerows(tbl)
  return (f"{len(tbl)-1} rows {len(tbl[0])} cols "
          f"klass={tbl[0][-1]} ({len({r[-1] for r in tbl[1:]})} values)")

if __name__ == "__main__":
  args = sys.argv[1:]
  out  = Out
  if "--out" in args:
    k = args.index("--out"); out = args[k+1]; del args[k:k+2]
  keep, drop = wanted(suite(), mine())
  if "--list" in args or not os.path.isdir(out):
    print(f"{'dataset':38}{'did':>7}{'rows':>8}{'cols':>6}{'klass':>6}")
    for d in keep:
      print(f"{d['name']:38}{d['did']:>7}{d['rows']:>8}{d['cols']:>6}"
            f"{d['klass']:>6}")
    print(f"\n{len(keep)} to add, {len(drop)} dropped")
    for d, why in drop:
      if "in moot" not in why: print(f"  {d['name']:38} {why}")
    sys.exit(0)
  only = [a for a in args if not a.startswith("-")]
  for d in keep:
    if only and d["name"] not in only: continue
    try:    note = fetch(d, out)
    except Exception as e: note = f"FAIL {type(e).__name__}: {e}"
    print(f"{d['name']:38} {note}", flush=True)
