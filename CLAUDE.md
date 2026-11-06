# CLAUDE.md

Experiments on the `tab` learner. The library itself lives next door in
`../tab` (github.com/timm/tab); this repo holds the rigs, the scores and
the argument. Nothing here is shipped.

`,/sh` is the work shell. It sets `TAB` to the sibling checkout and puts
it on `LUA_PATH`, so an edit in `../tab` is live here with no reinstall.
Do **not** `luarocks make` for development: that copies the file into
the rocks tree, and the local luarocks targets Lua 5.5 while everything
here runs under luajit (5.1).

**`../tab/tab.lua` is generated from `../tab/tab.yue`** (moved there
2026-11-05; it used to live in this repo). Edit the `.yue` and run
`../tab/,/build`, which prints a sha1 to pin a corpus to. An edit to
`tab.lua` is lost at the next build. The rigs here -- `etc/forest-eg.lua`,
`etc/fft-eg.lua`, `etc/rnb-eg.lua` -- take `TABDIR` so one build can be
pointed at, rather than recompiled per data set.

    ,/sh            the work shell
    ,/run nb        rerun an arm over moot, into cache/
    ,/again         the fast edit -> figure loop (bypasses any caching)
    etc/hpo.lua     sweep one knob against the label budget
    etc/charts.py   draw the figures in docs/
    docs/rq.md      the full argument. Read this first.
    attic/          dead code kept only as provenance; see attic/README.md

Data is [moot](https://github.com/timm/moot) at `~/gits/moot` (535M).
Scores live in `cache/`, one csv per dataset per arm.

## House style (same as tab)

ALLCAPS class table, Camel constructor, lowercase plain function. In a
function declaration, **any parameters after a run of two or more spaces
are scratch locals, not real parameters** -- they arrive `nil` and
document the function's working set.

A split is a seed, not a file: `rint` is Park-Miller and stays under
2^53, so lua, python and lisp shuffle a table into the same order. Only
scores reach the disk. Never use `math.random` -- its stream differs
across Lua builds and the results stop reproducing.

## What has already been tried

Do not re-run these without a reason to think something has changed.

**Nothing to tune.** Across five label budgets, `m` in {0,1,4} is
indistinguishable from the default `m=2` -- Cohen's d, Cliff's delta and
KS all agree, every time; win counts 358/353/355/365. `bins` bites
harder but still picks no winner: no setting is best at more than two of
the five budgets. Tuning here fits seed noise.

**More labels is not monotone.** The all-labels arm is better on
aggregate yet *worse* than the 45-label arm on 48 of 125 sets. The
m-estimate explains it: at 45 rows the pull toward the grand mean keeps
the ranking conservative; with every row the shrinkage vanishes and one
confidently wrong bin mean can push a bad row to the top.

**Labels stop helping near 100.** A 300x increase in data buys single
digits. The rest is structural -- one mean per bin per column cannot see
interactions.

**Rejected attempts to improve naive Bayes** (all measured over 69-73
sets, macro-averaged pd/pf/d2h):

| attempt | result |
|---|---|
| info-gain column weighting | -4 to -6 accuracy |
| AODE | worse on the macro metrics -- but see the contradiction below |
| per-cluster naive Bayes | 51 of 69 sets identical |
| MDL (Fayyad-Irani) discretization | -4.1 |
| bottom-up entropy merging | statistical tie |
| kNN, four sampling schemes | worse everywhere, 12.6x slower |

What survived: binning test rows on **training** statistics (+2.5), and
`bins=10 m=0.5` (+1.6, and small enough to be overfitting).

The ceiling: naive Bayes ~80.1 mean accuracy, LightGBM 82.8, TabICL
86.6. A real gain means beating the booster, not tuning the Bayes.

**The tree was starved, not weak** (Nov 3). `tab` ships `depth=4
leaf=8`, so a tree holds at most 8 leaves: it cannot name audiology's
24 klasses, and on a 14-row set `2*leaf` exceeds the data so nothing
splits at all. Every set we lost worst on was a many-klass or
conjunctive one (audiology -19, anneal -12, tic-tac-toe -11, letter
-10, vowel -10 against LightGBM). `etc/knobs.py` sweeps the knobs and
writes nothing to `cache/`; it puts the plateau at **depth=12 leaf=2**,
worth +13 on those sets. Column subsampling at `cols=3` costs ~5
points; all-columns and `sqrt(#x)` tie, so bag members use `sqrt`.

| arm | acc | pd | pf | d2h | auc |
|---|---|---|---|---|---|
| nb72 | 79.4 | 72.4 | 14.1 | 0.255 | 0.846 |
| treedeep (one deep tree) | 79.2 | | | | |
| boostdeep | 82.5 | | | | |
| bagbodeep | 83.4 | | | | |
| **fordeep** (30 deep trees, sqrt cols) | **83.6** | 75.5 | 13.6 | 0.243 | 0.863 |
| **either** (fordeep or nb, picked on train) | **83.8** | 76.5 | 13.0 | 0.229 | 0.862 |
| lgbm | 82.8 | 76.6 | 13.7 | 0.231 | 0.848 |
| tabicl | 86.6 | 81.5 | 11.4 | 0.188 | 0.885 |

Read that carefully. On **accuracy** and **auc** the deep forest is
ahead of LightGBM, but all three tests call it `same` -- parity, not a
win, and parity is already the first time tab has reached the booster.
On **d2h** LightGBM still wins more sets (43 of 69 against `fordeep`),
so the macro picture is a tie at best. TabICL is untouched.

`Either` is the useful idea, not the bigger number: NB and a deep
forest own *different* sets (NB heart.c 87.4 vs a deep tree's 74.3;
the forest letter 82.2 vs NB's 70.2), so it holds out a quarter of
TRAIN, scores both, and refits the winner on all of train. No test row
is touched. It is +1.8 on NB over all 73 sets.

Cost, mean seconds to fit one 80% split over the same 69 sets: nb72
0.011, fordeep 7.24 (median 0.39), lgbm 6.80 (median 2.50). So the
forest is ~6x faster than LightGBM in the median and much worse in the
tail (max 212s on letter against LightGBM's 53s) -- the cut search is
O(rows x cols x bins) and nothing prunes it. Measured under parallel
load, so treat it as a shape, not a number.

Forest size pays, slowly: on the same slices, bag=10/30/60/100 scores
weak 86.4/88.0/88.6/88.7 and auc .885/.897/.904/.908. Past 30 trees
you buy a tenth of a point per doubling, and auc a little more.

Still open: boosting adds nothing over the plain deep forest
(`boostdeep` 82.5, `bagbodeep` 83.4, both under `fordeep` 83.6), which
is suspicious -- SAMME over deep trees may need a learning rate.

Defects found in the rigs while measuring this (all fixed): `rank.py`
used a flat 0.5 tie band, so on auc's 0-1 scale every set was a tie;
`rank.py` and `sig.py` counted a *bigger* pf or d2h as a win; and in
`charts.py` the `arms` figure shadowed the `arms` helper, so `clas`
could not be drawn at all (helper is now `ranarms`).

**Faster forest: 4.66x, same answers** (Nov 5-6). Four changes to
`tab.yue`'s cut search, each measured against the 40-file identity
check (8 sets x nb, hardeep, hardeepauc, treedeep, treedeepauc):

| change | vs original | results |
|---|---|---|
| pooled allocations in `TAB.cut` | 1.64x | byte-identical |
| cdata points + inlined sort | 2.03x | byte-identical |
| binned cut search (`cuts`) | 2.41x | approximate |
| histogram, numeric and symbolic | **4.66x** | indistinguishable |

`luajit -jp=vf` found 45% of a forest run in the garbage collector,
86% of it under `cut`, which built `rows x cols` throwaway tables at
every node of every tree. Pooling those is the 1.64x and costs
nothing. After that `-jp=l` put 55% in `table.sort`'s comparator --
C calling back into Lua once per comparison, which the JIT cannot
inline.

The histogram wins by NOT sorting and by NOT accumulating. `Sym.add`
keeps an entropy cache (`cl + c*log c`), so the old search spent a
`log` per row per column per node; counting into `(bin x klass)` and
taking entropy from cumulative counts at the boundaries replaces
~3N logs with a few hundred. Klass strings are coded to integers
once per node, so no inner loop hashes a string. `symHist` does the
same for symbolic columns and is EXACT -- every value still
considered, same sorted order -- which retired `SYM.cut`'s O(V*R)
rescan.

Over 115 sets at `cuts=51`: pd 83.7 vs 83.7, pf 21.9 vs 21.9, auc
.878 vs .877, with wins and losses balanced (58/44, 55/47, 51/53)
and every median delta exactly 0. That is tie-cascade noise, not
degradation. `cuts=0` remains the default and is still byte-identical
to the published corpus.

**`cuts` sets resolution, not range.** Written the other way round at
first -- a fixed `sd/2` bin width with `cuts` widening the span --
which made 13 and 101 bins behave identically, since almost nothing
lies beyond 3sd to reach. That bug produced a whole afternoon of
"binning costs quality" results. It does not: at `cuts=13`
hypothyroid's auc is .829, at `cuts=51` it is .982, at 101 it is .996
against .999 exact.

**`cutTill` is not worth keeping.** Recomputing bin edges from each
node's rows (`cutTill=12`) is slower AND slightly worse than taking
the column's own mu/sd once (`cutTill=0`): 88.6 vs 88.8 accuracy for
78% more time. With `leaf=2`, by the time global edges stop
discriminating the node is too small to split anyway.

**Rejected this round:**

| attempt | result |
|---|---|
| FFT pruning (`etc/fft-eg.lua`) | 2-klass only: 82.8 vs the forest's 84.5 at 17x less time. Many-klass collapses (43.3 vs 94.2) and auc is last of six arms (.825 vs .890) -- a chain gives `k+1` regions where a tree gives `#leaves`, and the vote-share posterior has only `k+1` distinct values to rank by. Raising the label ceiling 13 -> 29 changed nothing; the limit is regions, not labels. |
| random naive Bayes (`etc/rnb-eg.lua`) | +0.6 pd over plain nb, worse auc and pf. `COLS=all` reproduces nb exactly, so bagging alone does nothing; column subspaces subtract information monotonically (sqrt 77.0, half 81.2, all 81.8); 10 members and 100 members are the same model. Bagging pays for UNSTABLE learners and NB is a closed-form count -- Breiman's condition fails. Untested and not covered by that argument: boosting NB, which creates diversity by reweighting the target. |

**Timing on this box needs the MINIMUM of several runs.** Four
separate traps cost hours here: my own concurrent jobs; mean-over-reps
including JIT warmup vs median-rep; a kernel benchmark whose size
distribution did not match the real workload (one sort of 1080 where
the tree does thousands of tiny ones); and, worst, Apple silicon
scheduling a whole run onto an efficiency core, which triples
`os.clock()` -- CPU time -- for identical work. Medians do not help
with the last one because it lands on entire runs. Two benchmarks
disagreed 3.6x on unchanged code before this was understood.

## Open and unresolved

**AODE.** `docs/rq.md` reports AODE as the better classifier (82.8 vs
81.5); a later macro-averaged rerun found it worse, and `tab.lua` dropped
it. Probably plain accuracy vs macro pd/pf/d2h on different corpora.
Settle this before citing either number.

## Known defects in the record

- An early rig binned test rows using columns summarised over **all** the
  training data while training on a sample, leaking the x distribution
  into every small-sample condition and flattening the label curve by
  construction. Fixed; numbers in `rq.md` are post-fix.
- `delta.elevators.csv` is excluded, so the regression corpus is 60, not
  61. `delta.ailerons.csv` was repaired outside the repo.
- `TAB.head` skips any column whose name ends in a capital `X`. That is
  deliberate (moot uses `idX`, `centerX`), but it silently drops `SEX`,
  `NOX`, `TAX`, `WAX` -- 4 of letter's 16 features, 9 of bank32nh's, 16
  sets in all. Both the lua and python readers share the rule, so
  comparisons stay fair.
- Timings were measured under parallel load. A clean single-threaded
  pass is needed before `secs.png` carries a strong claim.

## Ancestry

The learner was `jiffy.lua` in github.com/timm/lisp (904 commits, HEAD
`df5d10f`). That repo still holds the Common Lisp line -- `arms.lisp`,
`tree.lisp`, `ezr.lisp`, `lib.lisp`/`lib.md` and the pandoc doc chain --
which did not move here. Note `tab`'s own `origin/26oct25` branch is
**not** jiffy's pre-history; it is an unrelated older project.
