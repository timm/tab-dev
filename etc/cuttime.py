#!/usr/bin/env python3
"""cuttime.py: Forest(30) build time, three cut implementations.

One panel per corpus.  x is the data sets, sorted by what `cut4`
costs, so cut4 is the smooth line and the other two are read as
distance from it -- the question is "what does the rewrite cost
HERE", and sorting each series on itself (as `profile` does) would
throw away exactly the pairing that answers it.

Colours come from `charts.Look`, so the three lines inherit the
CVD-checked quartet the rest of docs/ already uses: black for the
code that ships, and the two warm hues for the rewrites.
"""
import os, sys, csv, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

Src  = sys.argv[1] if len(sys.argv) > 1 else "/tmp/bench.csv"
Docs = os.getenv("DOCS") or os.path.join(os.path.dirname(
         os.path.dirname(os.path.abspath(__file__))), "docs")
# black / orange / dark red: the three best-separating steps of the
# palette validated in `charts.py`.  Solid, dashed, solid -- the dash
# marks the version nobody is proposing, so the eye can drop it.
Arm = [("the93", "#000000", "-",  "the 93 lines, as shipped"),
       ("cut3",  "#D55E00", "--", "cut3  (39 lines, no memo)"),
       ("cut4",  "#860c4f", "-",  "cut4  (44 lines, bin memo)")]

rows = list(csv.DictReader(open(Src)))
# Only the corpora that have numbers.  A run still in flight should
# draw what it has rather than three panels of which two are blank
# frames -- an empty axis reads as "measured, found nothing".
Kinds = [k for k in ("classify", "regression", "optimize")
         if any(r["kind"] == k for r in rows)]
f, ax = plt.subplots(1, len(Kinds), figsize=(5.5 * len(Kinds), 5.6),
                     dpi=200, sharey=True, squeeze=False)
ax = ax[0]
for k, kind in enumerate(Kinds):
  a  = ax[k]
  rs = [r for r in rows if r["kind"] == kind]
  rs = [r for r in rs if float(r["cut4"]) > 0]   # a set too small to time
  rs.sort(key=lambda r: float(r["cut4"]))
  a.spines[["top", "right"]].set_visible(False)
  a.grid(axis="y", color="#eeeeee", zorder=0)
  for key, col, ls, lab in Arm:
    ys = [float(r[key]) for r in rs]
    # The legend carries the median RATIO, not the median time: the
    # times span four decades across a corpus, so a median second is
    # a number about which sets are big, and the ratio is the number
    # the decision rests on.
    rat = st.median([float(r[key]) / float(r["the93"]) for r in rs])
    a.plot(range(len(rs)), ys, ls, color=col, lw=1.8, zorder=3,
           label=f"{lab}   median {rat:.2f}x   total {sum(ys):,.0f}s")
  a.set_yscale("log")
  # Right edge, not left: the legend sits upper left and the "10 s"
  # label landed inside it.  The curves rise to the right, so a label
  # there would collide with the data instead -- except at the top,
  # which is the one gridline the curves pass under.  Anchor all
  # three to the right and let the axis grow a little past the last
  # point so there is room.
  a.set_xlim(-1, len(rs) + .08 * len(rs))
  for y, t in ((.001, "1 ms"), (.1, "100 ms"), (10, "10 s")):
    a.axhline(y, color="#dddddd", lw=1, zorder=1)
    a.text(len(rs) + .07 * len(rs), y, t, fontsize=8, color="#999999",
           ha="right", va="bottom")
  a.legend(frameon=False, fontsize=8, loc="upper left")
  a.set_title(f"moot/{kind}   ({len(rs)} sets)", fontsize=11)
  a.set_xlabel("data sets, sorted by what cut4 costs", fontsize=10)
ax[0].set_ylabel("seconds for one Forest(30) build\n"
                 "mean of 3, log scale", fontsize=11)
f.suptitle("What the simpler histogram cut costs: Forest(30) build time"
           "   (rows capped at 5,000; serial)", fontsize=13)
f.tight_layout()
f.savefig(f"{Docs}/cuttime.png", bbox_inches="tight"); plt.close(f)
print(f"{Docs}/cuttime.png")
