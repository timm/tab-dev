"""caps.py: tab2's forest(30) at several per-klass caps.
usage: pypy3 caps.py <dir holding tab2.py> out.csv set...
Per set and split: one untimed warm fit, one timed fit, scored on the
untouched 20%.  auc is tab2's weighted one (test klass frequencies)."""
import sys, os, time, random, statistics as st
sys.path.insert(0, sys.argv[1]); import tab2 as m
D = os.path.expanduser("~/gits/moot/classify")
Caps   = tuple(int(c) for c in os.getenv("CAPS", "0,50,100,200,400").split(","))
Splits = tuple(range(1, int(os.getenv("SPLITS", 3)) + 1))
with open(sys.argv[2], "w") as out:
  out.write("set,train,klasses,biggest,smallest,cap,secs,acc,wauc,macro\n")
  for name in sys.argv[3:]:
    got = {c: [] for c in Caps}
    for seed in Splits:
      random.seed(seed)
      data = m.Tab(f"{D}/{name}.csv")
      rows = data.rows[:]; random.shuffle(rows)
      k = int(.8 * len(rows))
      train, test = data.clone(rows[:k]), rows[k:]
      at = train.klass.at
      for c in Caps:
        m.the.cap = c
        m.Forest(train)
        t = time.perf_counter(); f = m.Forest(train)
        s = time.perf_counter() - t
        a = m.aucs(f, test)
        got[c].append((s, sum(f.guess(r) == r.raw[at] for r in test)
                          / len(test), a[0], a[2]))
    h = train.klass.has
    for c in Caps:
      s, acc, w, mac = (st.fmean(x[j] for x in got[c]) for j in range(4))
      out.write(f"{name},{len(train.rows)},{len(h)},{max(h.values())},"
                f"{min(h.values())},{c},{s:.4f},{acc:.4f},{w:.4f},{mac:.4f}\n")
      out.flush()
    print(name, "done", flush=True)
