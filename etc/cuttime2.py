#!/usr/bin/env python3
"""cuttime2.py: Forest(30) build time, five cut implementations.

One panel per corpus.  x is the data sets, sorted by what the SHIPPED
code costs, so `the93` is the smooth line and every other arm is read
as distance from the thing it would replace.  (The three-arm version
sorted by cut4; with cut4 demoted to one candidate among three, the
baseline is the only line all the ratios share.)

y is log seconds: the corpora span four decades, and the question is
a multiplier, not a difference.

Identity is never colour alone -- each arm also has its own dash --
because the whole figure is four near-parallel lines and a reader
with a colour deficit would otherwise be guessing.  Colours are
Okabe-Ito, which is published CVD-safe; the skill's validator was
not in the bundle to confirm it locally.
"""
import csv, statistics as st, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

Src  = sys.argv[1] if len(sys.argv) > 1 else "bench2.csv"
Dst  = sys.argv[2] if len(sys.argv) > 2 else \
       "/Users/timm/gh/tab-dev/docs/cuttime2.png"
Base = "the93"

#                key      colour     dash          label
Arm = [("the93", "#000000", (0, ()),             "the 94, as shipped (3 globals)"),
       ("cut4",  "#D55E00", (0, (5, 2)),         "cut4   44 lines  Sym per bin"),
       ("cut6",  "#860c4f", (0, (7, 2, 1, 2)),   "cut6   61 lines  Sym, reused"),
       ("cut8",  "#009E73", (0, (9, 3)),         "cut8   79 lines  one sweep"),
       ("cut5",  "#0072B2", (0, (1, 1.4)),       "cut5   96 lines  the 94, de-globaled")]

rows  = list(csv.DictReader(open(Src)))
Kinds = [k for k in ("classify", "regression", "optimize")
         if any(r["kind"] == k for r in rows)]
f, ax = plt.subplots(1, len(Kinds), figsize=(5.8 * len(Kinds), 5.8),
                     dpi=200, sharey=True, squeeze=False)
ax = ax[0]

for k, kind in enumerate(Kinds):
  a  = ax[k]
  rs = [r for r in rows if r["kind"] == kind]
  rs.sort(key=lambda r: float(r[Base]))
  for key, col, dash, lab in Arm:
    ys  = [float(r[key]) for r in rs]
    rat = st.median([float(r[key]) / float(r[Base]) for r in rs])
    a.plot(range(len(rs)), ys, color=col, linestyle=dash,
           lw=2.0 if key == Base else 1.7, zorder=3,
           label=f"{lab}\n      median {rat:.2f}x   total {sum(ys):,.0f}s")
  a.set_yscale("log")
  a.set_xlim(-1, len(rs) + .10 * len(rs))
  a.set_title(f"moot/{kind}   ({len(rs)} sets)", fontsize=11)
  a.set_xlabel(f"data sets, sorted by `{Base}` cost")
  if k == 0: a.set_ylabel("seconds to build Forest(30)   [log]")
  for y, t in ((.001, "1 ms"), (.01, "10 ms"), (.1, "100 ms"),
               (1, "1 s"), (10, "10 s")):
    a.axhline(y, color="#e8e8e8", lw=1, zorder=1)
    a.text(len(rs) + .09 * len(rs), y, t, fontsize=8, color="#999999",
           ha="right", va="bottom")
  for s in ("top", "right"): a.spines[s].set_visible(False)
  a.tick_params(labelsize=8)
  a.legend(fontsize=7.4, loc="upper left", frameon=False,
           labelspacing=.9, handlelength=3.2)

f.suptitle("What the histogram cut costs: four implementations, "
           "one machine, serial", fontsize=13, y=.99)
f.text(.5, .008,
  "LuaJIT, os.clock, 3 reps, rows capped at 5,000, one arm at a time."
  "  Each arm builds its own table, so no arm inherits another's bin"
  " memo.\nMedian is the per-set ratio to `the93`, not the ratio of the"
  " totals -- the totals are owned by the few biggest sets.",
  ha="center", fontsize=8, color="#555555")
f.tight_layout(rect=[0, .035, 1, .965])
f.savefig(Dst, bbox_inches="tight")
print(Dst)

for kind in Kinds:                        # the same numbers, as text
  rs = [r for r in rows if r["kind"] == kind]
  print(f"\n{kind}  (n={len(rs)})")
  for key, _, _, lab in Arm:
    q = sorted(float(r[key]) / float(r[Base]) for r in rs)
    print(f"  {key:6s} median {st.median(q):5.2f}x   "
          f"p90 {q[int(.9*len(q))]:5.2f}x   worst {q[-1]:5.2f}x   "
          f"total {sum(float(r[key]) for r in rs):8.1f}s")
