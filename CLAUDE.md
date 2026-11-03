# CLAUDE.md

Experiments on the `tab` learner. The library itself lives next door in
`../tab` (github.com/timm/tab); this repo holds the rigs, the scores and
the argument. Nothing here is shipped.

`,/sh` is the work shell. It sets `TAB` to the sibling checkout and puts
it on `LUA_PATH`, so an edit in `../tab/tab.lua` is live here with no
reinstall. Do **not** `luarocks make` for development: that copies the
file into the rocks tree, and the local luarocks targets Lua 5.5 while
everything here runs under luajit (5.1).

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
