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
| per-cluster naive Bayes | 51 of 69 sets identical -- UNVERIFIED, see below |
| MDL (Fayyad-Irani) discretization | -4.1 |
| bottom-up entropy merging | statistical tie |
| kNN, four sampling schemes | worse everywhere, 12.6x slower |

What survived: binning test rows on **training** statistics (+2.5), and
`bins=10 m=0.5` (+1.6, and small enough to be overfitting).

**The per-cluster row does not say identical to WHAT.** It arrived in
the Oct 28 bulk import with no commit message, no surviving rig (`grep
-i cluster` over every `.lua`/`.py`/`.yue` finds only `etc/charts.py`
and `attic/jiffy*`, none of them this experiment) and no cache arm --
`treenb` is naive Bayes at tree LEAVES, which is a different thing.
Under this table's heading the reading has to be "identical to plain
`nb`", i.e. clustering first and fitting per cluster changed no
prediction; that is a reconstruction from context, not a record.  The
69-set corpus also predates CC18's 116.  Do not cite this to rule an
experiment out: re-run it, or leave it alone.

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

**Faster forest: 6.7x end to end, same answers** (Nov 5-6). The cut
search was rebuilt in two rounds. Every row below is a CLEAN
measurement: one process holding both libraries, timings INTERLEAVED
so the E-core scheduler cannot favour whichever ran first, MINIMUM of
5 (scheduling only ever adds), whole forest builds on 14 real sets,
single threaded, nothing else on the machine.

| change | vs original | results |
|---|---|---|
| histogram cut search (replaces the sort) | 2.23x | indistinguishable |
| + bin ids and klass codes cached on the row | **6.72x** | indistinguishable |

Sum of seconds over the 14 sets: 22.75 -> 3.25, a 6.99x that agrees
with the 6.72x geometric mean. The two stages measured separately
multiply to 6.58x, which agrees with the 6.72x measured end to end --
so the decomposition is real and not an artifact of either run.

**A 10.15x was claimed for the first stage and it was wrong.** That
number came from corpus wall clock with `-P 5` on BOTH sides. The old
search is far more garbage-collection heavy, and five concurrent
GC-heavy processes punish each other more than five lean ones do, so
contention flattered the new code by a factor of four. Measured
single threaded, that stage is 2.23x. Any speedup taken from a
parallel corpus run is measuring the scheduler as much as the code --
the reason `secs.png` still carries the warning below.

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
- **The tab-vs-LightGBM seconds are not a comparison.** `etc/lgbm.py`
  times with `time.time()` -- wall -- and never set `n_jobs`, so
  LightGBM took all 10 cores; `tab-eg.lua` times with `os.clock()` --
  cpu -- on one thread. Different units, and both ran under `xargs
  -P 5`, which for LightGBM is 50-way oversubscription and for tab is
  exile to the e-cores. Two errors in opposite directions. `n_jobs` and
  `REPS` are now settable from the environment (`LGBM_JOBS=1` for the
  per-core question, unset for as-shipped). **Measured 2026-11-06**,
  per fit, startup excluded by construction (both programs time their
  own reps), minimum over 3 interleaved runs, quiet machine, lgbm at
  `n_jobs=1` -- the only setting where its `time.time()` and tab's
  `os.clock()` denote the same thing -- over the 14-set timing list:

      tab 2.088s   lgbm 5.061s   2.42x by sum, 1.52x geometric mean
      tab wins 7 of 14 sets and loses 7

  So the ~9x on `raw.png` is wrong by about 4x, and the real result is
  a split decision: tab wins where klasses are many (MiceProtein
  11.8x, audiology 6.7x, primary.tumor 6.1x) and loses on binary sets
  (credit.g 0.18x, kr.vs.kp 0.35x, diabetes 0.46x). Two things made
  the old number: python plus `import lightgbm` costs 1.31s per
  process against luajit's 0.039s, and LightGBM's default threading
  costs it **4.6x** on sets this small -- thread setup exceeds the
  work -- which `-P 8` then multiplied.

  A first attempt at this measurement was itself wrong, in the same
  way as everything else here: it ran tab straight after an all-core
  lgbm run, so tab landed on the e-cores and `os.clock()` read 3x
  high (waveform5000, 1.59s/rep there against 0.50s/rep alone). Any
  timing harness that interleaves a threaded arm with a single
  threaded one has to be read as suspect until a minimum, not a mean,
  says otherwise.

  `raw.png`, `rawclas.png`, `secs.png` and `cost.png` still read the
  `secs` column out of the `-P 8` corpus caches and are NOT fixed by
  the above, which is a separate 14-set harness. Repairing them needs
  a clean corpus-wide pass: about 25 min for tab, 45 for lgbm, and
  roughly 35 hours for tabicl, which is why the honest option is to
  stop putting seconds on a figure whose three curves were each
  measured a different way. `auc.png` and `pdpf.png` read no `secs`
  and are unaffected.
- **moot's klass markers mistyped six classify sets** (fixed upstream in
  moot `37d9853`). The `!` had been appended to the last column, which
  in four sets is a continuous feature, so `wine`, `spectf.test`,
  `spectf.train` and `spectrometer` came back with a Num klass and a
  classification-only `Tree` could not run at all; `mnist_1` had the
  right column in the wrong case. Worse, `spambase` has a feature
  counting occurrences of `!`, named `CHAR_FREQ_!`, whose trailing `!`
  collided with the marker -- so it was read as a goal and dropped from
  the x columns, and **every spambase number before this was learned
  from 56 features, not 57**. `credit.g` and `sponge` each had a
  categorical column summarised as a number. All eight were rerun; any
  cache or figure older than that commit is stale for those sets.
- `bridges.version1` and `bridges.version2` carry two rows each whose
  klass is `?`. A leaf holding only those has no majority, so `mid` is
  nil and `BAG.tally` indexes on nil -- seed-dependent, so it looks
  intermittent. `nb` does not crash; it scores `?` as if it were a
  klass. 2 sets of 120, 2 rows of 107, so the contamination is small,
  but it is there and unfixed.
- `pf` scored an undefined measurement as a perfect one. When a test
  split lands all-one-klass, that klass has no negatives, so there is
  no false alarm rate -- and both scorers wrote 0. `fp + tn` is
  `N - n_k`, so the guard fires exactly when one klass is the whole
  split, which means no second klass survives it: the whole rep has no
  `pf`, `d2h`, `macropf` or `macrod2h`. Fixed in `tab-eg.lua`'s
  `BAG.score1`/`BAG.score` and `etc/score.py`'s `macro`, which now
  report a `klasses` column as the sentinel, the same bargain `AucCols`
  already made. `charts.py` reads `pf` and `d2h` through `pfs()`, and
  everything through `vals()`.
  50 of 2300 forest reps, concentrated in 6 tiny sets; the bias is
  **downward**, so it flattered every arm. Only two medians move:
  `weather` pf 0.0 -> 16.7 and `shuttle.landing.control` 0.0 -> 66.7
  (a 15-row set, 17 of 20 reps degenerate). Verified lua and python
  agree digit-for-digit on the degenerate and normal cases, and that
  `acc` and `pd` are unchanged on every rep of 7 sets.

  **The caches and every figure predate the fix.** A cache with no
  `klasses` column reads exactly as it did before -- checked over 6376
  columns -- so old figures still draw, at their old numbers. The
  corpus has not been regenerated.

## Ancestry

The learner was `jiffy.lua` in github.com/timm/lisp (904 commits, HEAD
`df5d10f`). That repo still holds the Common Lisp line -- `arms.lisp`,
`tree.lisp`, `ezr.lisp`, `lib.lisp`/`lib.md` and the pandoc doc chain --
which did not move here. Note `tab`'s own `origin/26oct25` branch is
**not** jiffy's pre-history; it is an unrelated older project.
