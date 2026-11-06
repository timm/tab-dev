#!/usr/bin/env python3
"""charts.py: the figures in rq.md, drawn from ~/tmp/cache.

Every point is one data set's median over 20 seeds.  An arm is a
<who>.csv in that set's cache dir, so a new learner joins a chart
by being run, not by being coded here.

usage: python3 ,/charts.py [clas|labels|top5|secs ...]   (all, if none)
"""
import os, sys, glob, statistics as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import min as M
from math import log, exp
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

Cache = os.path.expanduser(os.getenv("CACHE", "~/tmp/cache"))
Docs  = os.getenv("DOCS") or os.path.join(os.path.dirname(
          os.path.dirname(os.path.abspath(__file__))), "docs")
Moot  = os.path.expanduser("~/gits/moot")

# one look per arm: colour, line style, marker, legend name
Look = {
  "nb":        ("#9ad7fb", "-",  "o", "naive Bayes (self-tuned)"),
  "rmeans":    ("#a6cee3", "-",  "o", "rmeans, 45 labels"),
  "rmeansall": ("#1f5f9e", "-",  "o", "rmeans, every row"),
  "nb50":      ("#1f5f9e", "--", "D", "naive Bayes, 50 labels"),
  "nb72":      ("#9ad7fb", "-",  "o", "naive Bayes (bins=7, m=2)"),
  "lgbm":      ("#e9622e", "-",  "o", "LightGBM"),
  "tabicl":    ("#860c4f", "-",  "s", "TabICLv2"),
  "tabpfn":    ("#e7298a", "--", "^", "TabPFN-3"),
  "treemaj":   ("#d9661f", "-",  "o", "tree, majority at the leaf"),
  "treenb":    ("#6a3d9a", "-",  "s", "tree, naive Bayes at the leaf"),
  "treeraw":   ("#b2df8a", ":",  "o", "tree, raw columns"),
  "forraw":    ("#7fbf7b", "--", "v", "bagged trees, raw columns"),
  "bagboraw":  ("#4a9c6d", "-.", "D", "boosted bags, raw columns"),
  "boostraw":  ("#1b7837", "-",  "^", "boosted trees, raw columns"),
  "treedeep":  ("#b2df8a", ":",  "o", "tree, deep (depth=12 leaf=2)"),
  "fordeep":   ("#7fbf7b", "-",  "v", "forest of 30 deep trees"),
  "for60":     ("#1b7837", "-",  "v", "forest of 60 deep trees"),
  "either60":  ("#122b0f", "-",  "*", "60-tree forest or naive Bayes, "
                                      "chosen on train"),
  "boostdeep": ("#7fbf7b", "--", "^", "boosted deep trees"),
  "bagbodeep": ("#4a9c6d", "-.", "D", "boosted bags of deep trees"),
  "either":    ("#122b0f", "-",  "*", "deep forest or naive Bayes, "
                                      "chosen on train"),
  "hardeep":   ("#1f5f9e", "--", "s", "forest of 30, hard vote"),
  # Two arms tried and rejected (see tab-dev/CLAUDE.md).  They are
  # listed so a cache holding them can be drawn; the live cache does
  # not, so the glob below keeps them out of the standing figures.
  "fft":       ("#d95f02", ":",  "P", "best frugal chain off one tree"),
  "rnb":       ("#8c6bb1", ":",  "X", "30 naive Bayes, subspaces"),
  # The same forest, with the numeric cut search done over `cuts`
  # bins instead of every distinct value -- no sort at all.  Drawn
  # beside `hardeep` so the approximation is visible, not assumed.
  "hardbin":   ("#e6550d", "-.", "D", "forest of 30, 13-bin cuts"),
  # The histogram build: same 30-tree forest, cut search done by
  # counting into (bin x klass) rather than accumulating `Sym`s.
  "hardhist":  ("#31a354", "-.", "^", "forest of 30, histogram cuts")}

# A short name per arm, for places where the long one does not fit.
# The strip above each panel prints five of these side by side, and
# the long names ran off the right edge of the figure -- text that
# leaves the canvas is not a styling problem, it is a number the
# reader cannot see.  The legend carries both, so the two vocabularies
# are tied together once, where the reader meets them.
Short = {"nb": "bayes", "nb72": "bayes", "treedeep": "1tree",
         "hardeep": "30tree", "lgbm": "lgbm", "tabicl": "tabicl",
         "tabpfn": "tabpfn", "treemaj": "1tree", "treenb": "1tree+nb",
         "fordeep": "30tree", "for60": "60tree", "rmeans": "rmeans",
         "rmeansall": "rmeans-all", "fft": "fft", "rnb": "rnb",
         "hardbin": "30tree/bin", "hardhist": "30tree/hist"}

def short(w):
  "WHO's short name, reaching through an -auc suffix."
  return Short.get(w) or Short.get(w[:-3]) or w

def agree(ax, names, a, b, tol, note=None):
  """Shade the sets where `a` and `b` land within `tol` of each other.

  The question a reader asks of these figures is not "which line is
  on top" but "where is the cheap arm already as good as the dear
  one".  A grey column says: on this set, these two agree.  `tol` is
  in the measure's own units -- 5 points of a percentage, 0.05 of an
  auc -- so it means the same fraction of full scale either way.
  """
  hit = [i for i, n in enumerate(names)
         if a.get(n) is not None and b.get(n) is not None
         and abs(a[n] - b[n]) <= tol]
  for i in hit:
    ax.axvspan(i - .5, i + .5, color="#000000", alpha=.07, lw=0, zorder=0)
  return hit

def dashes(ax, step):
  "Dashed guides every STEP, unlabelled: a ruler, not more numbers."
  ax.yaxis.set_minor_locator(MultipleLocator(step))
  ax.grid(axis="y", which="minor", color="#dddddd", lw=.6,
          linestyle=(0, (2, 3)), zorder=0)
  ax.tick_params(axis="y", which="minor", length=0)

# Name a band by the group its rows are actually in.  Zipping the
# three names onto the spans breaks the moment a band is empty: with
# no 3-5 klass set in the corpus there is one edge, not two, and the
# 6+ span silently takes the "3-5 klasses" label.
Band = ("2 klasses", "3-5 klasses", "6+ klasses")

def cells(dir, who, col):
  "Column COL of DIR's WHO.csv, one number per rep."
  f = f"{dir}/{who}.csv"
  if not os.path.exists(f): return None
  rows = [l.split(",") for l in open(f).read().splitlines() if l.strip()]
  at   = rows[0].index(col) if col in rows[0] else None
  if at is None: return None
  try:    return [float(r[at]) for r in rows[1:]]
  except (ValueError, IndexError): return None

# Red and bold on a chart's x axes marks the sets where its two
# arms part by at least this many pd points.  Computed, not listed,
# so the marks are reproducible and mean one definite thing; and
# computed once on pd, so the same sets stay marked across pd, pf
# and auc even though each panel sorts them differently.
PdMark = float(os.getenv("PDMARK", 10))

def aucs(dir, who):
  """DIR's WHO auc, one per rep, skipping the reps that have none.

  A split whose test rows all share one klass leaves every
  one-against-the-rest with no negatives, so there is no auc to
  report.  aucs() writes `0,0` there -- a zero klass count is the
  sentinel.  Averaging that zero in would score a missing
  measurement as a total failure, which is how six tiny sets came
  to look like every learner's worst case.
  """
  au, ks = cells(dir, who, "auc"), cells(dir, who, "klasses")
  if not au or not ks: return None
  return [a for a, k in zip(au, ks) if k > 0] or None

def sets(kind, need):
  "Every cached KIND set holding all of NEED, as (name, dir)."
  # moot/optimize nests one level deeper than the others, so look at
  # both depths; a group dir holds no csvs and drops out by itself.
  out = []
  for d in sorted(glob.glob(f"{Cache}/{kind}/*")
                  + glob.glob(f"{Cache}/{kind}/*/*")):
    if all(os.path.exists(f"{d}/{w}.csv") for w in need):
      out.append((os.path.basename(d), d))
  return out

def rows(name, kind):
  "How many rows that set's csv holds."
  f = glob.glob(f"{Moot}/{kind}/{name}.csv") + \
      glob.glob(f"{Moot}/{kind}/*/{name}.csv")
  if not f: return 0
  with open(f[0], errors="ignore") as h:
    h.readline(); return sum(1 for _ in h)

def klasses(name):
  "How many klasses that classify set has."
  f = glob.glob(f"{Moot}/classify/{name}.csv")
  if not f: return 0
  t = M.Tbl(f[0])
  c = [c for c in t.cols.y if c.txt.endswith("!")][-1]
  return len({r[c.at] for r in t.rows})

def fig(w=13, h=6):
  "One wide figure, 2600px across."
  f, ax = plt.subplots(figsize=(w, h), dpi=200)
  ax.spines[["top", "right"]].set_visible(False)
  ax.grid(axis="y", color="#eeeeee", zorder=0)
  return f, ax

def save(f, ax, name, title, xlab, ylab, rot=90, size=7):
  ax.set_title(title, fontsize=13, pad=18)
  ax.set_xlabel(xlab, fontsize=11, labelpad=12)
  ax.set_ylabel(ylab, fontsize=11)
  ax.tick_params(axis="x", labelsize=size, rotation=rot)
  f.tight_layout()
  f.savefig(f"{Docs}/{name}.png")
  plt.close(f)
  print(f"{Docs}/{name}.png")

# Sets called out on the x axis of labels.png and top5.png.  Override
# with MARK="a,b,c"; MARK="" turns it off.
MaeNear = float(os.getenv("MAENEAR", 5))   # grey band, raw mae

Mark = set(filter(None, os.getenv("MARK",
  "fried,stock,bodyfat,cpu.small,cpu.act,mv,pollution,2dplanes,"
  "gascons,detroit,bolts").split(",")))

def mark(ax, names, which=None):
  "Red and bold on the called-out sets.  Runs last, so it wins."
  for t, n in zip(ax.get_xticklabels(), names):
    if n in (Mark if which is None else which):
      t.set_color("#c0392b")
      t.set_fontweight("bold")

def ranarms(need, extra=("tabicl", "tabpfn")):
  """NEED, plus whichever foundation models have actually run.

  Not `arms`: that name belongs to the figure below, and a figure
  defined later silently shadowed this helper, so `clas` could not be
  drawn at all."""
  return list(need) + [w for w in extra
                       if glob.glob(f"{Cache}/*/*/{w}.csv")
                       or glob.glob(f"{Cache}/*/{w}.csv")]

# ---- the four figures ------------------------------------------------
def clas():
  "pd, pf and d2h on moot/classify: one vote per klass, no weights."
  who  = ranarms(["nb72", "fordeep", "lgbm"], ("tabicl", "tabpfn"))
  S    = sets("classify", ["nb72", "lgbm"])
  cols = [("pd", "pd %  (higher better)"), ("pf", "pf %  (lower better)"),
          ("d2h", "d2h  (lower better)")]
  med  = {(w, c): {n: st.fmean(cells(d, w, c) or [float("nan")])
                   for n, d in S} for w in who for c, _ in cols}
  only = os.getenv("ONLY")          # just the sets that arm changed
  if only:
    S = [(n, d) for n, d in S
         if cells(d, only, "acc") != cells(d, "nb72", "acc")]
  grp = {n: (0 if klasses(n) == 2 else 1 if klasses(n) <= 5 else 2)
         for n, _ in S}
  S.sort(key=lambda nd: (grp[nd[0]], med[("lgbm", "d2h")][nd[0]]))
  names = [n for n, _ in S]
  edge  = [j for j in range(1, len(names))          # where a group ends
           if grp[names[j]] != grp[names[j - 1]]]
  near  = {"pd": 5, "pf": 5, "d2h": .05}   # "the same", in each unit
  tie   = {c: {n: bool(cells(d, "nb72", c)) and bool(cells(d, "tabicl", c))
                  and abs(st.fmean(cells(d, "nb72", c))
                        - st.fmean(cells(d, "tabicl", c))) <= near[c]
               for n, d in S} for c, _ in cols}
  f, ax = plt.subplots(3, 1, figsize=(13, 10), dpi=200, sharex=True,
                       gridspec_kw=dict(hspace=.28))
  for k, (c, ylab) in enumerate(cols):
    a = ax[k]
    a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="y", color="#eeeeee", zorder=0)
    for j, n in enumerate(names):      # nb said nothing lgbm did not
      if tie[c][n]: a.axvspan(j - .5, j + .5, color="#ececec",
                                 lw=0, zorder=0)
    for j in edge: a.axvline(j - .5, color="#999999", lw=1, zorder=2)
    for w in who:
      ys = [med[(w, c)][n] for n in names]
      ok = [y for y in ys if y == y]
      col, ls, mk, lab = Look[w]
      a.plot(range(len(names)), ys, ls, color=col, marker=mk, ms=3, lw=1.6,
             label=lab, zorder=3)
    a.set_ylabel(ylab, fontsize=10)
    # An arm with nothing on THIS panel's sets is named, not averaged:
    # a corpus can grow faster than a slow arm can be run over it, and
    # a missing arm must not take the whole figure down.
    a.text(0, 1.015, "mean over sets:   " + "      ".join(
             ("{} {:.3g} \u00b1 {:.2g}".format(Look[w][3], st.fmean(v),
               st.pstdev(v)) if v else "{} n/a".format(Look[w][3]))
             for w, v in
             ((w, [y for y in [med[(w, c)][n] for n in names] if y == y])
              for w in who)),
           transform=a.transAxes, ha="left", va="bottom", fontsize=10.5,
           color="#333333")
    if k == 0:
      for lo, hi in zip([0] + edge, edge + [len(names)]):
        lab = Band[grp[names[lo]]]
        a.text((lo + hi - 1) / 2, .97, f"{lab}  (n={hi - lo})",
               transform=a.get_xaxis_transform(), ha="center", va="top",
               fontsize=9, color="#555555")
      a.plot([], [], lw=8, color="#ececec",
             label="naive Bayes (defaults) within 5 of TabICLv2")
      a.legend(frameon=False, fontsize=10, ncol=len(who) + 1,
               loc="lower center", bbox_to_anchor=(.5, 1.10))
  ax[0].set_title("Simple classifiers against a gradient booster and a"
                  " foundation model\n"
                  "(each score is the unweighted mean over the klasses;\neach point is one set's mean over 20 seeds)",
                  fontsize=13, pad=68)
  ax[2].set_xticks(range(len(names)))
  ax[2].set_xticklabels(names)
  ax[2].tick_params(axis="x", labelsize=7, rotation=90)
  ax[2].set_xlabel(f"{len(names)} moot/classify sets"
                   + (only and " where clustering ran" or "")
                   + ", sorted by LightGBM's d2h inside each group",
                   fontsize=11, labelpad=12)
  f.savefig(f"{Docs}/clas{only and '-' + only or ''}.png",
            bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/clas{only and '-' + only or ''}.png")

def gain():
  "What clustering changed, on the sets its gate let it run."
  S = [(n, d) for n, d in sets("classify", ["nb", "lgbm"])
       if cells(d, "nbc", "acc")
       and cells(d, "nbc", "acc") != cells(d, "nb", "acc")]
  cols = [("pd", "pd %", 1), ("pf", "pf %", -1), ("d2h", "d2h", -1)]
  mu   = lambda d, w, c: st.fmean(cells(d, w, c))
  S.sort(key=lambda nd: mu(nd[1], "nb", "d2h") - mu(nd[1], "nbc", "d2h"))
  names = [n for n, _ in S]
  f, ax = plt.subplots(1, 3, figsize=(13, 6.5), dpi=200, sharey=True)
  for k, (c, lab, good) in enumerate(cols):
    a  = ax[k]
    a.spines[["top", "right"]].set_visible(False)
    gs = [mu(d, "nbc", c) - mu(d, "nb", c) for _, d in S]
    a.barh(range(len(gs)), gs, color=["#33a02c" if g * good > 0
             else "#d9661f" for g in gs], zorder=3, height=.7)
    a.axvline(0, color="#333333", lw=1, zorder=4)
    a.set_title(f"{lab}   mean {st.fmean(gs):+.3g}", fontsize=11)
    a.grid(axis="x", color="#eeeeee", zorder=0)
    a.set_xlabel("per cluster  -  one model", fontsize=9)
  ax[0].set_yticks(range(len(names)))
  ax[0].set_yticklabels([f"{n}  (k={klasses(n)})" for n in names],
                        fontsize=8)
  f.suptitle("Naive Bayes, one model per cluster: what it changed\n"
             f"({len(names)} of 69 classify sets passed the gate;"
             " green is better)", fontsize=13)
  f.tight_layout()
  f.savefig(f"{Docs}/gain.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/gain.png")

def labels(kind="regression", name="labels", vs="lgbm"):
  "Raw MAE on moot/regression: 45 labels against everyone's all."
  who = ranarms(["rmeans", "rmeansall", "lgbm"])
  S   = sets(kind, ["rmeans", "rmeansall", "lgbm"])
  med = {w: {n: st.median(cells(d, w, "mae") or [float("nan")])
             for n, d in S} for w in who}
  # Grey marks "no real difference from rmeans on 45 labels".  Against
  # lgbm that is the three effect-size tests; against anything else it
  # is MaeNear, in raw mae units.  Mind that mae spans six orders of
  # magnitude here, so one flat window is generous on the small sets
  # and strict on the large.
  def near(d):
    a, b = cells(d, "rmeans", "mae"), cells(d, vs, "mae")
    if not a or not b: return False
    if vs == "lgbm":   return M.same(a, b)
    return abs(st.median(a) - st.median(b)) <= MaeNear
  tie = {n: near(d) for n, d in S}
  S.sort(key=lambda nd: med["rmeansall"][nd[0]] - med["lgbm"][nd[0]])
  names = [n for n, _ in S]
  f, ax = fig(13, 6)
  for j, n in enumerate(names):
    if tie[n]: ax.axvspan(j - .5, j + .5, color="#e8e8e8", zorder=0)
  for w in who:
    ys = [med[w][n] for n in names]
    if not any(y == y for y in ys): continue   # not run yet: no legend line
    c, ls, mk, lab = Look[w]
    ax.plot(range(len(names)), ys, ls, color=c, marker=mk, ms=2.5, lw=1.6,
            label=lab, zorder=3)
  ax.set_yscale("log")
  ax.set_xticks(range(len(names)))
  ax.set_xticklabels([f"{n} ({int(.8*rows(n,kind))})"
                      for n in names])
  for t, n in zip(ax.get_xticklabels(), names):
    if tie[n]: t.set_color("#999999")
  mark(ax, names)
  ax.plot([], [], lw=8, color="#e8e8e8",
          label="45 labels == LightGBM (cohen, cliffs, ks)" if vs == "lgbm"
          else f"45 labels within {MaeNear:g} mae of {Look[vs][3]}")
  ax.legend(frameon=False, fontsize=10, loc="upper left")
  save(f, ax, name, "rmeans on 45 labels vs every row of the 80%"
       " split, against LightGBM",
       f"{len(names)} moot/{kind} sets (training rows available),"
       " sorted by rmeans(all) - lgbm",
       "raw MAE, median of 20 seeds  (log)")

def top5(kind="regression", name="top5"):
  "Label only each arm's top 5: how good is the best of those?"
  who = ranarms(["rmeans", "rmeansall", "lgbm"])
  S   = sets(kind, ["rmeans", "rmeansall"])
  med = {w: {n: (lambda v: st.median(v) if v else float("nan"))(
                 cells(d, w, "rank")) for n, d in S} for w in who}
  S.sort(key=lambda nd: med["rmeans"][nd[0]])
  names = [n for n, _ in S]
  f, ax = fig(13, 6)
  ax.axhspan(0, 5, color="#eef4ee", zorder=0)
  ax.axhline(5, color="#2d7a2d", ls="--", lw=1.2, zorder=2,
             label="the 5% line")
  for w in who:
    ys = [med[w][n] for n in names]
    ok = [y for y in ys if y == y]
    if not ok: continue
    c, ls, mk, lab = Look[w]
    ax.plot(range(len(names)), ys, ls, color=c, marker=mk, ms=2.5, lw=1.6,
            label=f"{lab}  ({sum(1 for y in ok if y<=5)}/{len(ok)}"
                  " inside 5%)", zorder=3)
  ax.set_xticks(range(len(names)))
  ax.set_xticklabels([f"{n} ({int(.2*rows(n,kind))})"
                      for n in names])
  mark(ax, names)
  ax.set_ylim(bottom=0)
  ax.legend(frameon=False, fontsize=10, loc="upper left")
  save(f, ax, name, f"Label only the top 5 of each ranking:"
       f" how good is the best one?   [moot/{kind}]",
       "data sets (test rows), sorted by the 45-label result",
       "best of our top 5, as a percentile of the test set\n"
       "(0 = we found the very best row)")

def rate(v):
  "A speed-up reads as 651x; a slow-down needs its decimals."
  return f"{v:,.0f}x" if v >= 10 else f"{v:.2g}x"

def secs():
  "How many of this arm's runs fit inside one LightGBM run."
  mine = {"classify": "nb72", "regression": "rmeans"}
  who  = ranarms([], ("tabicl", "tabpfn")) + ["tab"]
  cur  = {w: [] for w in who}
  n    = 0
  for kind, ours in mine.items():
    for name, d in sets(kind, ["lgbm", ours]):
      base = st.median(cells(d, "lgbm", "secs"))
      n   += 1
      for w in who:
        v = cells(d, ours if w == "tab" else w, "secs")
        if v: cur[w].append(base / st.median(v))
  f, ax = fig(13, 5.8)
  Look["tab"] = ("#1f5f9e", "-", "",
               "tab.nb + tab.rmeans (bins=7,m=2)")
  # Draw the fastest arm first, so the legend reads top-to-bottom in
  # the same order as the curves.  Listed the other way round, the
  # slowest arm sits at the top of the legend and the chart reads
  # backwards.
  live = [w for w in who if cur[w]]
  live.sort(key=lambda w: st.median(cur[w]), reverse=True)
  for w in live:
    xs = sorted(cur[w])
    c, ls, mk, lab = Look[w]
    ax.plot(range(1, len(xs) + 1), xs, ls, color=c, lw=2,
            label=f"{lab}  (median {rate(st.median(xs))})", zorder=3)
  ax.set_yscale("log")
  ax.axhline(1, color="#333333", lw=1)
  ax.annotate("same speed as LightGBM", xy=(0.5, 1), xycoords=("axes fraction",
              "data"), ha="center", va="bottom", fontsize=9, color="#333333")
  ax.legend(frameon=False, fontsize=10, loc="upper left")
  save(f, ax, "secs",
       "How many runs of each arm fit inside one LightGBM run?",
       f"{n} moot classify+regression sets, each curve sorted on its own",
       "secs(LightGBM) / secs(arm)   (log)\n"
       "above the line = faster than LightGBM",
       rot=0, size=9)

def raw():
  "Absolute seconds per run, each task on its own panel."
  # One tab arm per panel: the forest where there are klasses to
  # vote on, rmeans where there are not.  `nb72` used to stand here,
  # but it was only ever run on the pre-CC18 sets, so the panel was
  # costing the corpus a third of itself to name an arm this figure
  # does not otherwise discuss.
  mine = (("classify", "hardeep"), ("regression", "rmeans"),
          ("optimize", "rmeans"))
  Lab  = {"hardeep": "tab forest of 30, hard vote",
          "rmeans":  "tab.rmeans (bins=7,m=2)"}
  who  = ranarms(["lgbm"], ("tabicl", "tabpfn")) + ["tab"]
  Look["tab"] = ("#1f5f9e", "-", "o", "tab")
  f, ax = plt.subplots(1, 3, figsize=(18, 5.8), dpi=200, sharey=True)
  for k, (kind, ours) in enumerate(mine):
    a, cur = ax[k], {w: [] for w in who}
    S = sets(kind, ["lgbm", ours])
    for name, d in S:
      for w in who:
        v = cells(d, ours if w == "tab" else w, "secs")
        if v: cur[w].append(st.fmean(v))
    a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="y", color="#eeeeee", zorder=0)
    for w in who:
      xs = sorted(cur[w])
      if not xs: continue
      c, _, _, lab = Look[w]
      if w == "tab": lab = Lab[ours]                    # per panel
      # Name each curve's own n beside its total.  A slow arm runs on
      # fewer sets, so the smaller total can be the dearer learner:
      # the totals are three corpora, not three columns.
      a.plot(range(1, len(xs) + 1), xs, "-", color=c, lw=2.2, zorder=3,
             label=f"{lab}   {len(xs)} sets, total {sum(xs):,.0f}s")
    a.set_yscale("log")
    for y, t in ((1, "1 second"), (60, "1 minute")):
      a.axhline(y, color="#cccccc", lw=1, zorder=1)
      if k == 0: a.text(1, y, " " + t, fontsize=8, color="#999999",
                        va="bottom")
    a.legend(frameon=False, fontsize=9, loc="upper left")
    a.set_title(f"moot/{kind}   ({len(S)} sets)", fontsize=11)
    a.set_xlabel("sets, each curve sorted on its own", fontsize=10)
  ax[0].set_ylabel("seconds for one fit and predict,\n"
                   "mean of 20 seeds  (log)", fontsize=11)
  f.suptitle("What one fit and predict costs", fontsize=13)
  f.tight_layout()
  f.savefig(f"{Docs}/raw.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/raw.png")

def rawclas():
  """Absolute seconds per run, the five classification arms only.

  raw.png puts classify beside regression and optimize, and there the
  tab arm has to be whichever one that task has -- a forest where
  there are klasses to vote on, rmeans where there are not.  One task
  needs no such substitution, so all five arms of the klass story can
  stand in one panel and be read against each other directly: the two
  single models, the two ensembles, and the neural one.

  Sorted per curve, not per set.  A cost curve answers "what does
  this arm cost across a corpus", and pairing the sets would answer
  a different question badly -- the arms do not agree on which set
  is the expensive one.
  """
  who = [w for w in ("nb", "treedeep", "hardeep", "hardhist", "lgbm", "tabicl")
         if glob.glob(f"{Cache}/classify/*/{w}.csv")]
  S   = sets("classify", who)
  cur = {w: sorted(st.fmean(v) for _, d in S if (v := cells(d, w, "secs")))
         for w in who}
  lab = dict(Look); lab["nb"] = Look["nb72"]
  f, a = plt.subplots(figsize=(10, 6.2), dpi=200)
  a.spines[["top", "right"]].set_visible(False)
  a.grid(axis="y", color="#eeeeee", zorder=0)
  for w in who:
    xs = cur[w]
    if not xs: continue
    # Each curve's own n beside its total: a slow arm that ran on
    # fewer sets can show the smaller total and still be the dearer
    # learner.  These are five corpora, not five columns.
    a.plot(range(1, len(xs) + 1), xs, "-", color=lab[w][0], lw=2.2,
           zorder=3, label="{}: {}   {} sets, total {:,.0f}s".format(
             short(w), lab[w][3], len(xs), sum(xs)))
  a.set_yscale("log")
  # Up to 1000s whatever the data reaches.  A log axis cropped to the
  # slowest arm makes that arm look pinned to the ceiling, and the
  # ceiling then moves every time a slower set lands -- so two
  # redraws of the same figure would not be comparable.
  a.set_ylim(top=1e3)
  top = max(max(v) for v in cur.values() if v)
  for y, t in ((1, "1 second"), (60, "1 minute"), (3600, "1 hour")):
    if y <= top:
      a.axhline(y, color="#cccccc", lw=1, zorder=1)
      # Right-hand end, not left: the legend sits top-left, and at
      # 1 minute the label landed underneath it.
      a.text(1, y, t + " ", fontsize=8, color="#999999", va="bottom",
             ha="right", transform=a.get_yaxis_transform())
  a.legend(frameon=False, fontsize=9, loc="upper left")
  a.set_xlabel(f"{len(S)} moot/classify sets, each curve sorted on its own",
               fontsize=10, labelpad=10)
  a.set_ylabel("seconds for one fit and predict,\n"
               "mean of 20 seeds  (log)", fontsize=11)
  a.set_title("What one fit and predict costs on a klass problem",
              fontsize=13, pad=14)
  f.tight_layout()
  f.savefig(f"{Docs}/rawclas.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/rawclas.png")

def cost():
  "Seconds against training rows: how each arm grows with the data."
  mine = {"classify": "nb72", "regression": "rmeans"}
  who  = ranarms(["lgbm"], ("tabicl", "tabpfn")) + ["tab"]
  Look["tab"] = ("#1f5f9e", "-", "o",
               "tab nb+rmeans (bins=7,m=2)")
  pts  = {w: [] for w in who}
  for kind, ours in mine.items():
    for name, d in sets(kind, ["lgbm", ours]):
      n = .8 * rows(name, kind)
      if n < 1: continue
      for w in who:
        v = cells(d, ours if w == "tab" else w, "secs")
        if v: pts[w].append((n, st.fmean(v)))
  f, ax = fig(13, 6.5)
  for w in who:
    xy = sorted(pts[w])
    if len(xy) < 2: continue
    xs = [a for a, _ in xy]; ys = [b for _, b in xy]
    lx = [log(a) for a in xs]; ly = [log(b) for b in ys]
    mx, my = st.fmean(lx), st.fmean(ly)       # least squares in log-log:
    v = sum((a - mx) ** 2 for a in lx)        # the slope is the exponent
    k = sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / v if v else 0
    c, _, mk, lab = Look[w]
    ax.plot(xs, ys, "", color=c, marker=mk, ms=3.5, lw=0, alpha=.55,
            zorder=3)
    ax.plot(xs, [exp(my + k * (a - mx)) for a in lx], "-", color=c, lw=2,
            label=f"{lab}   secs ~ rows^{k:.2f}", zorder=4)
  ax.set_xscale("log"); ax.set_yscale("log")
  ax.legend(frameon=False, fontsize=10, loc="upper left")
  save(f, ax, "cost", "What one fit and predict costs, as the data grows",
       "training rows (80% of the set)  (log)",
       "seconds, mean of 20 seeds  (log)", rot=0, size=9)

# ---- auc ------------------------------------------------------------
# tab.lua's SAME.ok, in python: two samples are the same when all three
# tests say so.  Thresholds are tab's, not retuned here.
def same(xs,ys):
  "True when XS and YS are one sample by cohen, cliffs and ks alike."
  a, b = sorted(xs), sorted(ys)
  if len(a) < 2 or len(b) < 2: return False
  sd = ((len(a)-1)*st.pstdev(a)**2 + (len(b)-1)*st.pstdev(b)**2)
  sd = (sd / (len(a)+len(b)-2)) ** .5
  if abs(st.fmean(a) - st.fmean(b)) / (sd + 1e-32) > .35: return False
  gt = lt = j = k = 0                                      # cliffs delta
  for x in a:
    while j < len(b) and b[j] <  x: j += 1; k = j
    while k < len(b) and b[k] == x: k += 1
    gt, lt = gt + j, lt + len(b) - k
  if abs(gt - lt) / (len(a)*len(b)) > .195: return False
  p = q = d = 0                                            # kolmogorov
  while p < len(a) and q < len(b):
    v = min(a[p], b[q])
    while p < len(a) and a[p] == v: p += 1
    while q < len(b) and b[q] == v: q += 1
    d = max(d, abs(p/len(a) - q/len(b)))
  return d / ((len(a)+len(b)) / (len(a)*len(b))) ** .5 <= 1.36

def auc():
  """auc on every moot/classify set: does the pd gap survive ranking?

  pd and d2h score one threshold; auc scores the whole ordering.  pd
  itself is clas.png's story, so only auc is drawn here, grouped by
  klass count the same way clas.png groups.

  A set leaves when some rep produced no auc at all -- every klass
  missing positives from that test split, so the macro mean is a mean
  over nothing -- or when both arms sit below chance, having no
  ordering to rank.  Set AUCALL=1 to keep 3-5 klasses only.
  """
  # tab's own arm leads, not the naive Bayes.  Three arms only: the
  # forest, the booster it set out to match, and the model neither
  # reaches.  Grey asks one question -- is the forest TabICL yet?
  who = tuple(["hardeepauc", "lgbmauc"]
              + [w for w in ("tabiclauc", "tabpfnauc",
                             "treedeepauc", "nbauc", "fftauc", "rnbauc",
                             "hardbinauc", "hardhistauc")
                 if glob.glob(f"{Cache}/classify/*/{w}.csv")])
  Pair = ("hardeepauc", "tabiclauc")   # what the sort and sd strip use
  # Complete cases only: every arm drawn had to run on every set
  # shown.  A mean over 106 sets beside a mean over 87 is two
  # different questions printed as one row, and the sort key -- the
  # gap to TabICL -- has no value at all on a set TabICL skipped.
  S   = sets("classify", list(who))
  if os.getenv("AUC35"): S = [(n,d) for n,d in S if 3 <= klasses(n) <= 5]
  # A 20% test split under this many rows cannot carry an auc: one
  # row moving swings it by a tenth.  Computed, not listed by name,
  # so the exclusion is reproducible and means one definite thing.
  Mintest = 10
  keep, gone = [], []
  for n, d in S:
    ks = [k for w in who if (k := cells(d, w, "klasses"))]
    au = [st.fmean(a) for w in who if (a := aucs(d, w))]
    if (min(min(k) for k in ks) > 0 and max(au) >= .5
        and int(.2 * rows(n, "classify")) >= Mintest): keep.append((n, d))
    else: gone.append(n)
  print(f"  auc: kept {len(keep)} of {len(S)}; dropped {' '.join(gone)}")
  raw = {w: {n: v for n, d in keep if (v := aucs(d, w))}
         for w in who}
  med = {w: {n: st.fmean(v) for n, v in d.items()} for w, d in raw.items()}
  has = lambda w, n: n in med[w]          # an arm that declined this set
  grp = {n: (0 if klasses(n) == 2 else 1 if klasses(n) <= 5 else 2)
         for n, _ in keep}
  # Inside each band, by TabICL's own auc, ascending -- the same key
  # pdpf.png sorts on, so a set sits in a comparable place in both
  # figures and the two can be read against each other.
  #
  # SORTBY=gap restores the older key: how far the hard-vote forest
  # sits from TabICL, left losing worst and right caught up.  That
  # one answers "is the forest TabICL yet"; this one answers "where
  # is this corpus hard".
  Sortby = os.getenv("SORTBY", "hardeep")
  if Sortby == "gap":
    keep.sort(key=lambda nd: (grp[nd[0]],
                              med[Pair[0]][nd[0]] - med[Pair[1]][nd[0]]
                              if all(has(w, nd[0]) for w in Pair) else 9))
    kname = "the gap to TabICL"
  else:
    lead = next((w for w in (Sortby + "auc", Sortby) if w in med), Pair[0])
    keep.sort(key=lambda nd: (grp[nd[0]], med[lead].get(nd[0], 9)))
    # Look gains its *auc aliases further down, after this sort, so
    # reach through to the base arm rather than depend on that order.
    kname = f"{Look[lead if lead in Look else lead[:-3]][3]}'s own auc"
  names = [n for n, _ in keep]
  edge  = [j for j in range(1, len(names))         # where a group ends
           if grp[names[j]] != grp[names[j - 1]]]
  def ends(n):
    "The lowest and highest scoring arms that ran on set N."
    ws = sorted((w for w in who if has(w, n)), key=lambda w: med[w][n])
    return raw[ws[0]][n], raw[ws[-1]][n]
  def pair(n):
    "The two arms sorted on, or None when one of them sat this out."
    return (None if not all(has(w, n) for w in Pair)
            else (raw[Pair[0]][n], raw[Pair[1]][n]))
  # The pooled sd of those two arms' 20 reps: the denominator cohen's d
  # divides by, and so the scale that says whether a gap above is real.
  def pooled(n,    a=None, b=None):
    a, b = pair(n) or ends(n)
    return (((len(a)-1)*st.pstdev(a)**2 + (len(b)-1)*st.pstdev(b)**2)
            / (len(a)+len(b)-2)) ** .5
  for w in who: Look[w] = Look[w[:-3]]   # eitherauc draws as either
  Look["nbauc"] = Look["nb72"]           # ,/run writes nb at bins=7
  # A thin strip of its own, not a second scale on the first: sd and
  # auc do not share units, and one axis per panel is the rule.
  f, (ax, sx) = plt.subplots(2, 1, figsize=(13, 7), dpi=200, sharex=True,
                             gridspec_kw=dict(height_ratios=[4, 1],
                                              hspace=.08))
  for a in (ax, sx):
    a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="y", color="#eeeeee", zorder=0)
  # Grey column: the new forest and TabICL land within 0.05 auc here
  # -- the same fraction of full scale as pdpf's 5 points.
  Near = ("tabiclauc", "hardhistauc")
  shade = (agree(ax, names, med[Near[0]], med[Near[1]], .05)
           if all(w in med for w in Near) else [])
  if shade: agree(sx, names, med[Near[0]], med[Near[1]], .05)
  for a in (ax, sx):
    for j in edge: a.axvline(j - .5, color="#999999", lw=1, zorder=2)
  # The full range, so a gap is read against the whole scale and not
  # against a window chosen to flatter it.
  Floor = 0
  for w in who:
    col, ls, mk, lab = Look[w]
    ax.plot(range(len(names)),
            [med[w][n] if has(w, n) else float("nan") for n in names],
            ls, color=col,
            marker=mk or "o", ms=4, lw=1.4,
            label="{}: {}".format(short(w), lab), zorder=3)
  ax.set_ylim(Floor, 1)
  dashes(ax, .05)            # auc runs 0-1, so 0.05 is the 5% step
  low = sorted((med[w][n], Look[w][3], n) for w in who for n in names
               if has(w, n) and med[w][n] < Floor)
  note = ""
  if low:
    note = ("\nthe axis starts at {:g}; below it, off scale:  "
            .format(Floor)
            + ";  ".join(f"{lab} {n} {v:.2f}" for v, lab, n in low))
  for lo, hi in zip([0] + edge, edge + [len(names)]):
    lab = Band[grp[names[lo]]]
    if hi > lo:
      ax.text((lo + hi - 1) / 2, .02, f"{lab}  (n={hi - lo})",
              transform=ax.get_xaxis_transform(), ha="center", va="bottom",
              fontsize=9, color="#555555")
  ax.legend(frameon=False, fontsize=10, ncol=len(who) + 1,
            loc="lower center", bbox_to_anchor=(.5, 1.07))
  # An arm can be missing from every set shown -- a corpus grows
  # faster than a slow arm can be run over it -- so name it and move
  # on rather than take the figure down.
  def avg(w,    v=None):
    v = [med[w][n] for n in names if has(w, n)]
    # .3f, not .3g: a mean that lands on 0.810 must not print as
    # 0.81 beside 0.893, or the eye reads a shorter number as a
    # coarser measurement.
    return ("{} {:.3f}{}".format(short(w), st.fmean(v),
              "" if len(v) == len(names) else f" (on {len(v)})")
            if v else "{} n/a".format(short(w)))
  # The means only.  A "best on N of M" tally used to sit here, and
  # it answered a question nobody was asking: with five arms inside
  # a few thousandths of each other on most sets, a count of outright
  # wins is decided by noise, not by which arm ranks better.  The
  # pooled-sd strip below already says how much of any gap is real.
  ax.text(0, 1.015, "mean over sets:   " + "      ".join(avg(w) for w in who),
          transform=ax.transAxes, ha="left", va="bottom", fontsize=10.5,
          color="#333333")
  sds = [pooled(n) for n in names]
  sx.bar(range(len(names)), sds, width=.62, color="#9aa5ad", lw=0,
         zorder=3)
  sx.set_ylim(0, max(sds) * 1.15)
  sx.set_ylabel("pooled sd", fontsize=9)
  sx.tick_params(axis="y", labelsize=8)
  sx.text(0, 1.04, "pooled sd of the hard-vote forest and TabICL:  median {:.3f}"
                   "   max {:.3f} ({})".format(
            st.median(sds), max(sds), names[sds.index(max(sds))]),
          transform=sx.transAxes, ha="left", va="bottom", fontsize=9,
          color="#555555")
  ax.set_ylabel("auc  (higher better)", fontsize=11)
  sx.set_xticks(range(len(names)))
  sx.set_xticklabels(names)
  sx.tick_params(axis="x", labelsize=6.5, rotation=90)
  sx.set_xlabel(f"{len(names)} moot/classify sets,"
                + f" sorted by {kname} inside each group" + note,
                fontsize=11, labelpad=12)
  # pad clears the legend, which sits above the axes, not inside it.
  ax.set_title("TabICL leads; tab's deep forest now matches LightGBM\n"
               "(each point is one set's mean over 20 random 80:20"
               " splits)", fontsize=13, pad=74)
  f.savefig(f"{Docs}/auc.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/auc.png")

def panels(name, who, vs, title, lead):
  """Three stacked panels -- pd, pf, auc -- for the arms in WHO.

  Every panel splits the sets into 2, 3-5 and 6+ klass bands, then
  orders each band by its own metric's gap from the first arm to VS.
  Each panel carries its own x labels, because a column is a
  different set in each.  Grey marks where that metric says those
  two arms are one sample, and the strip under auc pools that same
  pair's sd, so a gap can be read against the spread that made it.
  """
  base  = who[0]
  Short = {"nb": "nb", "treenb": "tree+nb", "lgbm": "LightGBM",
           "tabicl": "TabICLv2"}
  S  = sets("classify", list(who) + [w + "auc" for w in who])
  Of = (("pd",  "pd",  "",    1, (0, 100), .03, 20, 5),
        ("pf",  "pf",  "",   -1, (0, 64),  .93, 20, 5),
        ("auc", "auc", "auc", 1, (0, 1),   .03, .2, .05))
  raw = {}
  for n, d in S:
    v = {}
    for col, _, suf, _, _, _, _, _ in Of:
      for w in who:
        r = aucs(d, w + suf) if col == "auc" else cells(d, w + suf, col)
        if not r: break
        v[w, col] = r
      else: continue
      break
    else: raw[n] = v
  mu  = {n: {k: st.fmean(v) for k, v in d.items()} for n, d in raw.items()}
  big = {n for n in raw
         if abs(mu[n][vs, "pd"] - mu[n][base, "pd"]) >= PdMark}
  grp = lambda n: 0 if klasses(n) == 2 else 1 if klasses(n) <= 5 else 2
  f   = plt.figure(figsize=(13, 14), dpi=200)
  gs  = f.add_gridspec(len(Of), 1, hspace=.62, height_ratios=[4, 4, 5])
  sub = gs[len(Of) - 1].subgridspec(2, 1, hspace=.07, height_ratios=[4, 1])
  ax  = [f.add_subplot(gs[j]) for j in range(len(Of) - 1)] \
        + [f.add_subplot(sub[0])]
  sx  = f.add_subplot(sub[1])
  for a, (lab, col, suf, up, lim, at, maj, mnr) in zip(ax, Of):
    names = sorted(raw, key=lambda n: (grp(n),
                     up * (mu[n][vs, col] - mu[n][base, col])))
    edge  = [j for j in range(1, len(names))
             if grp(names[j]) != grp(names[j - 1])]
    tie   = [j for j, n in enumerate(names)
             if same(raw[n][base, col], raw[n][vs, col])]
    win   = {w: sum(1 for n in names
                    if up * (mu[n][w, col] - mu[n][base, col]) > 0)
             for w in who[1:]}
    a.spines[["top", "right"]].set_visible(False)
    a.yaxis.set_major_locator(MultipleLocator(maj))
    a.yaxis.set_minor_locator(MultipleLocator(mnr))
    # above the one-sample bands, which are near the grid's own grey
    # and would otherwise swallow the rules they cross.
    a.grid(axis="y", which="major", color="#c9c9c9", lw=.9, zorder=1.6)
    a.grid(axis="y", which="minor", color="#dedede", lw=.6, zorder=1.5)
    for j in tie:
      a.axvspan(j - .5, j + .5, color="#ececec", lw=0, zorder=0)
    for j in edge:
      a.axvline(j - .5, color="#999999", lw=.8, zorder=2)
    for w in who:
      c, ls, mk, nm = Look[w]
      a.plot(range(len(names)), [mu[n][w, col] for n in names], ls,
             color=c, marker=mk, ms=3.5, lw=1.3, label=nm, zorder=3)
    a.set_ylabel("{}  ({} better)".format(lab,
                 "higher" if up > 0 else "lower"), fontsize=10)
    if lim: a.set_ylim(*lim)
    a.set_xlim(-1, len(names))
    a.set_xticks(range(len(names)))
    a.tick_params(axis="x", labelsize=6, rotation=90)
    a.text(0, 1.015, "mean:   " + "   ".join(
             "{} {:.3g}".format(Short[w], st.fmean(mu[n][w, col]
                                                   for n in names))
             for w in who)
           + "      beats {}: ".format(Short[base])
           + ", ".join("{} {}".format(Short[w], win[w]) for w in who[1:])
           + ", of {};   {} and {} one sample on {}".format(
               len(names), Short[base], Short[vs], len(tie)),
           transform=a.transAxes, ha="left", va="bottom", fontsize=9.5,
           color="#333333")
    for lo, hi in zip([0] + edge, edge + [len(names)]):
      g = Band[grp(names[lo])]
      if hi > lo:
        a.text((lo + hi - 1) / 2, at, "{}  (n={})".format(g, hi - lo),
               transform=a.get_xaxis_transform(), ha="center",
               va="bottom", fontsize=8.5, color="#555555")
    if col != "auc":
      a.set_xticklabels(names); mark(a, names, big); continue
    a.set_xticklabels([])             # auc's labels go under the strip
    sds = [(((len(x) - 1) * st.pstdev(x) ** 2
              + (len(y) - 1) * st.pstdev(y) ** 2)
            / (len(x) + len(y) - 2)) ** .5
           for n in names
           for x, y in [(raw[n][base, col], raw[n][vs, col])]]
    sx.spines[["top", "right"]].set_visible(False)
    for j in tie:
      sx.axvspan(j - .5, j + .5, color="#ececec", lw=0, zorder=0)
    for j in edge:
      sx.axvline(j - .5, color="#999999", lw=.8, zorder=2)
    sx.bar(range(len(names)), sds, width=.62, color="#9aa5ad", lw=0,
           zorder=3)
    sx.set_xlim(-1, len(names)); sx.set_ylim(0, max(sds) * 1.15)
    sx.set_ylabel("pooled sd", fontsize=9)
    sx.tick_params(axis="y", labelsize=8)
    sx.set_xticks(range(len(names))); sx.set_xticklabels(names)
    sx.tick_params(axis="x", labelsize=6, rotation=90)
    mark(sx, names, big)
    # inside the auc panel, where nothing is drawn: the strip's own
    # top edge is the auc axis, and a caption there collides.
    a.text(0, .13, "pooled sd below, of {} and {}:   median {:.3f}"
                   "   max {:.3f} ({})".format(
             Short[base], Short[vs], st.median(sds), max(sds),
             names[sds.index(max(sds))]),
           transform=a.transAxes, ha="left", va="bottom", fontsize=9,
           color="#555555")
  ax[0].plot([], [], lw=8, color="#ececec",
             label="grey: {} and {} are one sample"
                   " (cohen, cliffs and ks all agree)".format(
                     Short[base], Short[vs]))
  ax[0].legend(frameon=False, fontsize=10, ncol=len(who) + 1,
               loc="lower center", bbox_to_anchor=(.5, 1.10))
  sx.set_xlabel("{} moot/classify sets, split into klass bands, each"
                " band sorted by its own {}-to-{} gap\n"
                "red: the {} sets where the two part by {:g} pd points"
                " or more".format(len(raw), Short[base], Short[vs],
                                  len(big), PdMark),
                fontsize=11, labelpad=10)
  ax[0].set_title(title + "\n" + lead, fontsize=13, pad=54)
  f.savefig(f"{Docs}/{name}.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/{name}.png")

def naming():
  "Look's own names are older than the rigs; say what the arms are."
  # ,/run passes no flags, so nb.csv is tab's own bins=7, m=2 -- the
  # same settings the tree's leaves use.
  Look["nb"]     = Look["nb"][:3] + ("naive Bayes (bins=7, m=2)",)
  Look["treenb"] = ("#16827d", "-", "s", "tree, naive Bayes at the leaf")

def tree():
  "The split, on its own: does cutting the rows first buy anything?"
  naming()
  panels("tree", ("nb", "treenb"), "treenb",
         "Does splitting first help a naive Bayes?",
         "(each point is one set's mean over 20 random 80:20 splits)")

def arms():
  "Naive Bayes against a booster and a foundation model."
  naming()
  panels("arms", ("nb", "lgbm", "tabicl"), "tabicl",
         "How far behind is a naive Bayes?",
         "(each point is one set's mean over 20 random 80:20 splits)")


def pdpf():
  """pd and pf at one threshold, the two panels in the SAME order.

  auc scores the whole ordering, and on an easy or a lopsided klass
  it sits near 1 while the arm still misses most of the positives --
  so an auc chart alone cannot tell "ranks well" from "the klass was
  easy".  pd and pf are that same answer read at the threshold the
  learner actually commits to.  Both panels carry one x order, set
  by pd, so a set that costs pd to buy pf is read straight down the
  column instead of hunted for twice.

  Five arms, three families: one model (naive Bayes, one deep tree),
  many models (LightGBM, a 30-tree forest), and a neural one
  (TabICLv2).  Complete cases only -- every arm ran on every set
  shown, so the means below compare on one corpus.
  """
  fam = [("nb",       "one model"),
         ("treedeep", "one model"),
         ("fft",      "one model"),
         ("lgbm",     "many models"),
         ("hardeep",  "many models"),
         ("hardhist", "many models"),
         ("rnb",      "many models"),
         ("tabicl",   "neural")]
  who = [w for w, _ in fam if glob.glob(f"{Cache}/classify/*/{w}.csv")]
  S   = sets("classify", who)
  cols = [("pd", "pd %   (higher better)"), ("pf", "pf %   (lower better)")]
  med = {(w, c): {n: st.fmean(v) for n, d in S if (v := cells(d, w, c))}
         for w in who for c, _ in cols}
  lab = dict(Look)
  lab["nb"] = Look["nb72"]              # ,/run writes nb at bins=7
  keep = [(n, d) for n, d in S
          if all(n in med[(w, c)] for w in who for c, _ in cols)]
  print(f"  pdpf: kept {len(keep)} of {len(S)}")
  grp = {n: (0 if klasses(n) == 2 else 1 if klasses(n) <= 5 else 2)
         for n, _ in keep}
  # Sorted inside each band on one arm's pd, ascending: the left of a
  # band is where that arm struggles, the right where the set is easy
  # for it.  Read that way the other four are a spread around a
  # rising reference line, and a set where a cheap arm matches an
  # expensive one shows up as a crossing.
  #
  # The cost of a single-arm key: it draws that arm smooth and every
  # rival as noise about it, and the smoothness is a property of the
  # sort, not a result.  So the arm sorted on is named on the x axis,
  # and SORTBY=mean restores the mean-pd key, which spends no arm's
  # shape to buy the reference line.
  Sortby = os.getenv("SORTBY", "hardeep")
  if Sortby == "mean" or Sortby not in who:
    key = {n: st.fmean([med[(w, "pd")][n] for w in who]) for n, _ in keep}
    kname = "mean pd"
  else:
    key, kname = med[(Sortby, "pd")], f"{lab[Sortby][3]}'s pd"
  keep.sort(key=lambda nd: (grp[nd[0]], key[nd[0]]))
  names = [n for n, _ in keep]
  edge  = [j for j in range(1, len(names))
           if grp[names[j]] != grp[names[j - 1]]]
  f, ax = plt.subplots(2, 1, figsize=(13, 8), dpi=200, sharex=True,
                       gridspec_kw=dict(hspace=.10))
  # Grey column: the new forest and TabICL land within 5 points here.
  # Both panels get the same columns, so a set that agrees on pd and
  # not on pf is visible as a column with one line apart in it.
  Near = ("tabicl", "hardhist")
  shade = {}
  if all(w in who for w in Near):
    for k, (c, _) in enumerate(cols):
      shade[c] = agree(ax[k], names, med[(Near[0], c)], med[(Near[1], c)], 5)
  for k, (c, ylab) in enumerate(cols):
    a = ax[k]
    a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="y", color="#eeeeee", zorder=0)
    for j in edge: a.axvline(j - .5, color="#999999", lw=1, zorder=2)
    for w in who:
      col, ls, mk, _ = lab[w]
      a.plot(range(len(names)), [med[(w, c)][n] for n in names], ls,
             color=col, marker=mk, ms=3.5, lw=1.5,
             label="{}: {}  [{}]".format(short(w), lab[w][3],
                                         dict(fam)[w]), zorder=3)
    a.set_ylim(0, 100)
    dashes(a, 5)                   # every 5%, unlabelled
    a.set_ylabel(ylab, fontsize=11)
    if c in shade:
      a.text(1, 1.012, "grey: {} of {} sets within 5 of {}".format(
               len(shade[c]), len(names), short(Near[0])),
             transform=a.transAxes, ha="right", va="bottom",
             fontsize=9, color="#777777")
    a.text(0, 1.012, "mean over sets:   " + "      ".join(
             "{} {:.1f}".format(short(w), st.fmean(
               [med[(w, c)][n] for n in names])) for w in who),
           transform=a.transAxes, ha="left", va="bottom",
           fontsize=10.5, color="#333333")
  for lo, hi in zip([0] + edge, edge + [len(names)]):
    t = Band[grp[names[lo]]]
    if hi > lo:
      ax[0].text((lo + hi - 1) / 2, .02, f"{t}  (n={hi - lo})",
                 transform=ax[0].get_xaxis_transform(), ha="center",
                 va="bottom", fontsize=9, color="#555555")
  # The legend sits above the panel, so the title has to be pushed
  # clear of however many rows it wraps to.  A fixed pad was right
  # for five arms and let a seventh arm's third row land on top of
  # the title.
  nrow = -(-len(who) // 3)
  ax[0].legend(frameon=False, fontsize=10, ncol=3,
               loc="lower center", bbox_to_anchor=(.5, 1.10))
  ax[1].set_xticks(range(len(names)))
  ax[1].set_xticklabels(names)
  ax[1].tick_params(axis="x", labelsize=6.5, rotation=90)
  ax[1].set_xlabel(f"{len(names)} moot/classify sets, both panels in one"
                   f" order: by {kname} inside each klass group",
                   fontsize=11, labelpad=12)
  ax[0].set_title("pd and pf at the threshold, where auc will not say\n"
                  "(each point is one set's mean over 20 random 80:20"
                  " splits)", fontsize=13, pad=28 + 15 * nrow)
  f.savefig(f"{Docs}/pdpf.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/pdpf.png")

if __name__ == "__main__":
  extra = {"optlabels": lambda: labels("optimize", "optlabels", vs="tabicl"),
           "opt":       lambda: top5("optimize", "opt")}
  jobs = sys.argv[1:] or ["clas", "labels", "top5", "optlabels", "opt",
                          "secs", "cost", "raw", "rawclas", "auc", "pdpf",
                          "tree", "arms"]
  for j in jobs: (extra.get(j) or globals()[j])()
