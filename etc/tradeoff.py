#!/usr/bin/env python3
"""tradeoff.py: what each learner costs, against what it scores.

Five arms on ONE slice -- the 14 sets knobs.py calls weak plus its
controls, 20 seeded 80:20 splits, the same splits for every arm
(`ens.pair`).  Not the 73-set corpus: this slice is deliberately
heavy on the many-klass sets, so every number here runs high and the
SPREAD is the point, not the level.

Every arm is read from cache/ -- `fordeep` is the 30-tree forest,
which etc/ablate.py's 32-tree `base` matched to 0.03 acc, so the
two sizes are one arm as far as this data can tell.  The
seconds are NOT one clean pass -- cache/ was filled under parallel
load -- so read the x axis as a shape, two decades at a time.

usage: tradeoff.py
"""
import os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

Docs = os.path.join(os.path.dirname(os.path.dirname(
         os.path.abspath(__file__))), "docs")

#       name              acc    secs   ours?
Arms = [("TabICLv2",      91.65, 6.551, 0),
        ("for60",         85.80, 0.574, 1),
        ("fordeep (30)",  85.15, 0.422, 1),
        ("LightGBM",      84.10, 6.739, 0),
        ("nb (bins=7)",   77.31, 0.002, 1)]

Ours, Thrs = "#1f5f9e", "#e9622e"      # validated pair, light surface
Ink, Mute  = "#1a1a1a", "#777777"

f, ax = plt.subplots(figsize=(9, 5.5), dpi=200)
ax.set_facecolor("#fcfcfb"); f.patch.set_facecolor("#fcfcfb")
ax.spines[["top", "right"]].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color("#cccccc")
ax.grid(color="#eeeeee", lw=1, zorder=0)
ax.set_axisbelow(True)

for nm, acc, sec, ours in Arms:
  ax.scatter(sec, acc, s=150, zorder=4,
             color=Ours if ours else Thrs,
             edgecolors="#fcfcfb", linewidths=2)   # a ring, so near
                                                   # marks stay apart
# labels placed by hand: for60 and tree32 sit 0.6 apart on y and
# would collide if both went right.
# dx<0 puts the label left of its mark: for60 and fordeep sit a
# tenth of a second apart and would otherwise write over each other.
At = {"TabICLv2": (13, 0), "for60": (13, 9), "fordeep (30)": (-13, -9),
      "LightGBM": (13, 0), "nb (bins=7)": (13, 0)}
for nm, acc, sec, ours in Arms:
  dx, dy = At[nm]
  ax.annotate(f"{nm}  {acc:.1f}", (sec, acc), textcoords="offset points",
              xytext=(dx, dy), fontsize=11, color=Ink, va="center",
              ha="left" if dx > 0 else "right")

ax.set_xscale("log")
ax.set_xlim(0.0012, 90)
ax.set_ylim(1, 100)
ax.set_xlabel("seconds to fit one 80:20 split  (log, mean over 14 sets)",
              fontsize=11, color=Ink)
ax.set_ylabel("accuracy  (higher better)", fontsize=11, color=Ink)
ax.tick_params(colors=Mute, labelsize=9)
ax.set_xticks([0.001, 0.01, 0.1, 1, 10])
ax.set_xticklabels(["0.001", "0.01", "0.1", "1", "10"])

ax.annotate("cheaper and better", xy=(0.0028, 12), fontsize=10,
            color=Mute, ha="left")
ax.annotate("", xy=(0.0022, 17), xytext=(0.02, 17),
            arrowprops=dict(arrowstyle="->", color=Mute, lw=1.2))
ax.plot([], [], "o", color=Ours, ms=9, label="tab")
ax.plot([], [], "o", color=Thrs, ms=9, label="baseline")
ax.legend(frameon=False, fontsize=10, loc="center right",
          labelcolor=Ink)
ax.set_title("30 deep trees pass LightGBM at a tenth of the cost;\n"
             "TabICL is still six points clear",
             fontsize=13, color=Ink, pad=14, loc="left")
f.savefig(f"{Docs}/tradeoff.png", bbox_inches="tight")
print(f"{Docs}/tradeoff.png")
