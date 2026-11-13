#!/usr/bin/env python3
"""cuttime3.py: what each rewrite of the histogram cut costs.

Seven implementations is too many for one absolute-time panel -- the
lines cross constantly and nothing is legible.  So this is the
performance profile the rest of this repo already uses: each arm's
307 per-set ratios to the shipped code, sorted on their own, read
against percentile.  Every line is monotone, so they separate; the
median is the midpoint and the right-hand tail is the worst case.

Reading it: 1.0 is the shipped code.  Below the line is faster.  A
flat line is a constant multiplier; a line that climbs steeply on the
right has a few sets it is bad at, and those are named in the text
report, not here.

What this figure cannot show, and the absolute-time version could:
that the ratio does not depend on how big the set is.  That is
checked numerically instead -- the Spearman of ratio against the
shipped code's own seconds is printed under the table.
"""
import csv, statistics as st, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

Src  = sys.argv[1] if len(sys.argv) > 1 else "bench3.csv"
Dst  = sys.argv[2] if len(sys.argv) > 2 else \
       "/Users/timm/gh/tab-dev/docs/cuttime.png"
Base = "the93"

#        key      colour     dash                 lines  globals  label
Arm = [("cut4",  "#D55E00", (0, (5, 2)),         44, 0, "Sym per bin, fresh"),
       ("cut6",  "#860c4f", (0, (7, 2, 1, 2)),   61, 0, "Sym per bin, reused"),
       ("cut8",  "#009E73", (0, (9, 3)),         79, 0, "one sweep, per-col buf"),
       ("cut10", "#56B4E9", (0, (3, 1, 1, 1)),   78, 0, "one sweep, one buf"),
       ("cut5",  "#0072B2", (0, (1, 1.4)),       96, 0, "the 94, per-col buf"),
       ("cut9",  "#CC79A7", (0, (6, 1.5)),       95, 0, "the 94, one buf")]

rows  = list(csv.DictReader(open(Src)))
Kinds = [k for k in ("classify", "regression", "optimize")
         if any(r["kind"] == k for r in rows)]
f, ax = plt.subplots(1, len(Kinds), figsize=(5.6 * len(Kinds), 5.4),
                     dpi=200, sharey=True, squeeze=False)
ax = ax[0]

for k, kind in enumerate(Kinds):
  a  = ax[k]
  rs = [r for r in rows if r["kind"] == kind]
  xs = [100 * i / (len(rs) - 1) for i in range(len(rs))]
  a.axhline(1.0, color="#000000", lw=2.2, zorder=4,
            label=f"the 94, as shipped   94 lines, 3 globals")
  for key, col, dash, loc, glob, lab in Arm:
    q = sorted(float(r[key]) / float(r[Base]) for r in rs)
    a.plot(xs, q, color=col, linestyle=dash, lw=1.7, zorder=3,
           label=f"{key}   {loc} lines, 0 globals   {lab}\n"
                 f"      median {st.median(q):.2f}x   p90 "
                 f"{q[int(.9*len(q))]:.2f}x")
  a.set_yscale("log")
  a.set_ylim(.22, 11)
  a.set_yticks([.25, .5, .75, 1, 1.5, 2, 3, 5, 10])
  a.set_yticklabels(["0.25x", "0.5x", "0.75x", "1x", "1.5x", "2x",
                     "3x", "5x", "10x"])
  a.set_title(f"moot/{kind}   ({len(rs)} sets)", fontsize=11)
  a.set_xlabel("percentile of data sets")
  if k == 0:
    a.set_ylabel("Forest(30) build time, relative to the shipped code")
  a.axhspan(.22, 1.0, color="#f2f8f2", zorder=0)
  for s in ("top", "right"): a.spines[s].set_visible(False)
  a.tick_params(labelsize=8)
  a.legend(fontsize=6.9, loc="upper left", frameon=False,
           labelspacing=.75, handlelength=3.0)

f.suptitle("Seven ways to write the histogram cut: what the clean ones "
           "cost", fontsize=13, y=.995)
f.text(.5, .006,
  "LuaJIT, os.clock, 3 reps, rows capped at 5,000, one arm at a time.  "
  "Each arm builds its own COPY of the rows, so no arm inherits another's"
  " bin memo:\n`TAB.add` keeps the row by reference, and without the copy"
  " the shipped code fills the cache its replacements are then credited "
  "for.\n\n"
  "The ratio is a PAIRED comparison -- all arms run back to back on one "
  "set -- which is why it survives a noisy box.  classify was run twice: "
  "cut9 and cut5\nreplicate to 1% (0.95x, 0.98x), cut8/cut10/cut6 move "
  "16-23% in the median, and the 94's own per-set seconds drift 31% "
  "between runs.  Read the\nslower arms as ranges (cut10 1.25-1.5x, cut4"
  " 2.5-2.8x); read the ORDER, which is stable, and cut9/cut5, which are "
  "not.",
  ha="center", fontsize=7.4, color="#555555")
f.tight_layout(rect=[0, .105, 1, .955])
f.savefig(Dst, bbox_inches="tight")
print(Dst)

def spearman(a, b):
  def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0] * len(v)
    for p, i in enumerate(s): r[i] = p
    return r
  ra, rb = rank(a), rank(b)
  n = len(a)
  return 1 - 6 * sum((x - y) ** 2 for x, y in zip(ra, rb)) / (n * (n*n - 1))

print(f"\n{'':8s} {'lines':>5s} {'glob':>4s} "
      + "  ".join(f"{k:>18s}" for k in Kinds))
print(f"{'the93':8s} {94:5d} {3:4d} " + "  ".join(f"{'1.00x (baseline)':>18s}"
                                                  for _ in Kinds))
for key, _, _, loc, glob, lab in Arm:
  cells = []
  for kind in Kinds:
    rs = [r for r in rows if r["kind"] == kind]
    q  = sorted(float(r[key]) / float(r[Base]) for r in rs)
    cells.append(f"{st.median(q):.2f}x  p90 {q[int(.9*len(q))]:.2f}x")
  print(f"{key:8s} {loc:5d} {glob:4d} " + "  ".join(f"{c:>18s}" for c in cells))

print("\nratio vs set size (Spearman of ratio against the93 seconds; "
      "0 = a constant multiplier):")
for key, _, _, _, _, _ in Arm:
  cs = []
  for kind in Kinds:
    rs = [r for r in rows if r["kind"] == kind]
    cs.append(f"{kind[:3]} {spearman([float(r[Base]) for r in rs], [float(r[key])/float(r[Base]) for r in rs]):+.2f}")
  print(f"  {key:7s} " + "   ".join(cs))
