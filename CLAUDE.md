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
