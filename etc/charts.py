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

Cache = os.path.expanduser(os.getenv("CACHE", "~/tmp/cache"))
Docs  = os.getenv("DOCS") or os.path.join(os.path.dirname(
          os.path.dirname(os.path.abspath(__file__))), "docs")
Moot  = os.path.expanduser("~/gits/moot")

# one look per arm: colour, line style, marker, legend name
Look = {
  "nb":        ("#a6cee3", "-",  "o", "naive Bayes (self-tuned)"),
  "rmeans":    ("#a6cee3", "-",  "o", "rmeans, 45 labels"),
  "rmeansall": ("#1f5f9e", "-",  "o", "rmeans, every row"),
  "nb50":      ("#1f5f9e", "--", "D", "naive Bayes, 50 labels"),
  "nb72":      ("#a6cee3", "-",  "o", "naive Bayes (bins=7, m=2)"),
  "lgbm":      ("#d9661f", "-",  "o", "LightGBM"),
  "tabicl":    ("#6a3d9a", "-",  "s", "TabICLv2"),
  "tabpfn":    ("#e7298a", "--", "^", "TabPFN-3")}

def cells(dir, who, col):
  "Column COL of DIR's WHO.csv, one number per rep."
  f = f"{dir}/{who}.csv"
  if not os.path.exists(f): return None
  rows = [l.split(",") for l in open(f).read().splitlines() if l.strip()]
  at   = rows[0].index(col) if col in rows[0] else None
  if at is None: return None
  try:    return [float(r[at]) for r in rows[1:]]
  except (ValueError, IndexError): return None

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

def mark(ax, names):
  "Red and bold on the called-out sets.  Runs last, so it wins."
  for t, n in zip(ax.get_xticklabels(), names):
    if n in Mark:
      t.set_color("#c0392b")
      t.set_fontweight("bold")

def arms(need, extra=("tabicl", "tabpfn")):
  "NEED, plus whichever foundation models have actually run."
  return list(need) + [w for w in extra
                       if glob.glob(f"{Cache}/*/*/{w}.csv")
                       or glob.glob(f"{Cache}/*/{w}.csv")]

# ---- the four figures ------------------------------------------------
def clas():
  "pd, pf and d2h on moot/classify: one vote per klass, no weights."
  who  = arms(["nb72", "lgbm"], ("tabicl", "tabpfn"))
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
    a.text(0, 1.015, "mean over sets:   " + "      ".join(
             "{} {:.3g} \u00b1 {:.2g}".format(Look[w][3], st.fmean(v),
               st.pstdev(v)) for w, v in
             ((w, [y for y in [med[(w, c)][n] for n in names] if y == y])
              for w in who)),
           transform=a.transAxes, ha="left", va="bottom", fontsize=10.5,
           color="#333333")
    if k == 0:
      for lo, hi, lab in zip([0] + edge, edge + [len(names)],
                             ("2 klasses", "3-5 klasses", "6+ klasses")):
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
  who = arms(["rmeans", "rmeansall", "lgbm"])
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
  who = arms(["rmeans", "rmeansall", "lgbm"])
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
  who  = arms([], ("tabicl", "tabpfn")) + ["tab"]
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
  mine = (("classify", "nb72"), ("regression", "rmeans"),
          ("optimize", "rmeans"))
  who  = arms(["lgbm"], ("tabicl", "tabpfn")) + ["tab"]
  Look["tab"] = ("#1f5f9e", "-", "o",
               "tab nb+rmeans (bins=7,m=2)")
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
      if w == "tab": lab = f"tab.{ours} (bins=7,m=2)"   # per panel
      a.plot(range(1, len(xs) + 1), xs, "-", color=c, lw=2.2, zorder=3,
             label=f"{lab}   total {sum(xs):,.0f}s")
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

def cost():
  "Seconds against training rows: how each arm grows with the data."
  mine = {"classify": "nb72", "regression": "rmeans"}
  who  = arms(["lgbm"], ("tabicl", "tabpfn")) + ["tab"]
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
  who = tuple(["nbauc", "lgbmauc"]
              + [w for w in ("tabiclauc", "tabpfnauc")
                 if glob.glob(f"{Cache}/classify/*/{w}.csv")])
  S   = sets("classify", ["nbauc", "lgbmauc"])
  if os.getenv("AUC35"): S = [(n,d) for n,d in S if 3 <= klasses(n) <= 5]
  keep, gone = [], []
  for n, d in S:
    ks = [k for w in who if (k := cells(d, w, "klasses"))]
    au = [st.fmean(a) for w in who if (a := cells(d, w, "auc"))]
    if min(min(k) for k in ks) > 0 and max(au) >= .5: keep.append((n, d))
    else: gone.append(n)
  print(f"  auc: kept {len(keep)} of {len(S)}; dropped {' '.join(gone)}")
  raw = {w: {n: v for n, d in keep if (v := cells(d, w, "auc"))}
         for w in who}
  med = {w: {n: st.fmean(v) for n, v in d.items()} for w, d in raw.items()}
  has = lambda w, n: n in med[w]          # an arm that declined this set
  grp = {n: (0 if klasses(n) == 2 else 1 if klasses(n) <= 5 else 2)
         for n, _ in keep}
  keep.sort(key=lambda nd: (grp[nd[0]],
                            med[who[0]][nd[0]]
                            - max(med[w][nd[0]] for w in who[1:]
                                  if has(w, nd[0]))))
  names = [n for n, _ in keep]
  edge  = [j for j in range(1, len(names))         # where a group ends
           if grp[names[j]] != grp[names[j - 1]]]
  def ends(n):
    "The lowest and highest scoring arms that ran on set N."
    ws = sorted((w for w in who if has(w, n)), key=lambda w: med[w][n])
    return raw[ws[0]][n], raw[ws[-1]][n]
  tie   = {n: same(*ends(n)) for n in names}
  # The pooled sd of the two arms' 20 reps: the denominator cohen's d
  # divides by, and so the scale that says whether a gap above is real.
  def pooled(n,    a=None, b=None):
    a, b = ends(n)
    return (((len(a)-1)*st.pstdev(a)**2 + (len(b)-1)*st.pstdev(b)**2)
            / (len(a)+len(b)-2)) ** .5
  for w in who: Look[w] = Look[w[:-3]]   # nbauc draws as nb72 does
  Look["nbauc"] = Look["nb72"]
  # A thin strip of its own, not a second scale on the first: sd and
  # auc do not share units, and one axis per panel is the rule.
  f, (ax, sx) = plt.subplots(2, 1, figsize=(13, 7), dpi=200, sharex=True,
                             gridspec_kw=dict(height_ratios=[4, 1],
                                              hspace=.08))
  for a in (ax, sx):
    a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="y", color="#eeeeee", zorder=0)
  for a in (ax, sx):
    for j, n in enumerate(names):     # the two arms are one sample here
      if tie[n]: a.axvspan(j - .5, j + .5, color="#ececec", lw=0, zorder=0)
    for j in edge: a.axvline(j - .5, color="#999999", lw=1, zorder=2)
  # auc floors at .5, not 0: below that line is what a coin would score.
  ax.axhline(.5, color="#999999", ls=":", lw=1, zorder=2)
  ax.text(len(names) - .5, .5, " chance", ha="left", va="center",
          fontsize=9, color="#666666")
  for w in who:
    col, ls, mk, lab = Look[w]
    ax.plot(range(len(names)),
            [med[w][n] if has(w, n) else float("nan") for n in names],
            ls, color=col,
            marker=mk or "o", ms=4, lw=1.4,
            label=lab, zorder=3)
  ax.set_ylim(0, 1)
  for lo, hi, lab in zip([0] + edge, edge + [len(names)],
                         ("2 klasses", "3-5 klasses", "6+ klasses")):
    if hi > lo:
      ax.text((lo + hi - 1) / 2, .02, f"{lab}  (n={hi - lo})",
              transform=ax.get_xaxis_transform(), ha="center", va="bottom",
              fontsize=9, color="#555555")
  ax.plot([], [], lw=8, color="#ececec",
          label="grey: one sample (cohen, cliffs and ks all agree)")
  ax.legend(frameon=False, fontsize=10, ncol=3, loc="lower center",
            bbox_to_anchor=(.5, 1.10))
  wins = sum(1 for n in names
             if med[who[0]][n] >= max(med[w][n] for w in who if has(w, n)))
  ax.text(0, 1.015, "mean over sets:   " + "      ".join(
            "{} {:.3g}{}".format(Look[w][3], st.fmean(
              [med[w][n] for n in names if has(w, n)]),
              "" if len(med[w]) == len(names)
                 else f" (on {len(med[w])})") for w in who)
          + "      least==most on {} of {};   naive Bayes best on {}".format(
              sum(tie.values()), len(names), wins),
          transform=ax.transAxes, ha="left", va="bottom", fontsize=10.5,
          color="#333333")
  sds = [pooled(n) for n in names]
  sx.bar(range(len(names)), sds, width=.62, color="#9aa5ad", lw=0,
         zorder=3)
  sx.set_ylim(0, max(sds) * 1.15)
  sx.set_ylabel("pooled sd", fontsize=9)
  sx.tick_params(axis="y", labelsize=8)
  sx.text(0, 1.04, "pooled sd of the least and most arms:  median {:.3f}"
                   "   max {:.3f} ({})".format(
            st.median(sds), max(sds), names[sds.index(max(sds))]),
          transform=sx.transAxes, ha="left", va="bottom", fontsize=9,
          color="#555555")
  ax.set_ylabel("auc  (higher better)", fontsize=11)
  sx.set_xticks(range(len(names)))
  sx.set_xticklabels(names)
  sx.tick_params(axis="x", labelsize=6.5, rotation=90)
  sx.set_xlabel(f"{len(names)} moot/classify sets,"
                " sorted by the auc gap inside each group",
                fontsize=11, labelpad=12)
  # pad clears the legend, which sits above the axes, not inside it.
  ax.set_title("Ranking closes most of the gap that pd opens\n"
               "(each point is one set's mean over 20 random 80:20"
               " splits)", fontsize=13, pad=58)
  f.savefig(f"{Docs}/auc.png", bbox_inches="tight"); plt.close(f)
  print(f"{Docs}/auc.png")

if __name__ == "__main__":
  extra = {"optlabels": lambda: labels("optimize", "optlabels", vs="tabicl"),
           "opt":       lambda: top5("optimize", "opt")}
  jobs = sys.argv[1:] or ["clas", "labels", "top5", "optlabels", "opt",
                          "secs", "cost", "raw", "auc"]
  for j in jobs: (extra.get(j) or globals()[j])()
