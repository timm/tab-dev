# Queue

Work agreed but not started.  Runs only after the TabICL jobs land and
the win/labels figures are redrawn -- those two jobs are timing runs
and nothing heavy shares the box with them.

## 0. Land what is already running

- job 2 (40 sets, `FORCE=1`): TabICL `win` + serial `secs`
- job 3 (7 never-run sets, `ROWS=50000`)
- then promote both into `cache/`, redraw
  `winreg winopt labelsreg labelsopt rawnum`

`fornumall` stays at 67 of 128 optimize sets by decision.  Those 67 are
the SMALL half -- 81/1343/17737 rows against 10000/10000/166975 for the
61 missing -- so any optimize figure that draws `fornumall` either
gates to the 67 and says n=67, or drops the arm.  Drawing it unmarked
makes a missing run look like a loss.

## 1. Attribute-weighted naive Bayes

Weight each column's log-likelihood term by how much it tells you about
the class.  tab bins every column, sym and num alike, so ONE formula
serves both -- that is the claim worth testing, more than the accuracy
delta.

    log P(y) + sum_a w_a * log P(bin_a | y)

Three constraints, each from a way the obvious version fails:

1. **Symmetric uncertainty, not raw infogain.**  `2*IG/(H(X)+H(Y))`.
   Raw gain rewards a column for being fine-grained.  num columns are
   bin-capped here and sym columns are not, so raw gain would upweight
   wide sym columns for their width.  SU normalises by column entropy
   and is the same expression for both types.
2. **Handle redundancy, not just relevance.**  SU-to-class is blind to
   column-column correlation, and correlation is NB's actual disease:
   two copies of one signal get counted twice, and relevance weighting
   upweights BOTH.  So drop correlated columns -- CFS-style, greedy on
   pairwise SU.  That is a second O(cols^2) pass, unlike (1).
3. **No knob.**  `w_a = SU_a / mean(SU)`, no exponent, no threshold.
   An exponent or a cutoff trades tab's no-HPO claim for a point of
   AUC.  Junk columns land near zero weight on their own.

Arms: `nbsu` (1+3) and `nbcfs` (1+2+3), beside `nb` on `auc.png` and
`pdpf.png`.  classify only -- NB runs nowhere else here -- so ~96 of
105 sets, about an hour.

**This has reportedly been measured and rejected before.**
`CLAUDE.md` carries `info-gain column weighting | -4 to -6 accuracy`.
But that row came in the Oct 28 bulk import under the commit message
`as`, with no surviving rig (`grep -riE 'infogain|nbw|colweight'` over
every `.lua`/`.py`/`.yue` finds nothing) and no cached csvs -- the same
provenance as the `per-cluster naive Bayes` row that `CLAUDE.md`
already marks UNVERIFIED.  It also does not say which weighting rule
it used, and raw gain is exactly the version (1) exists to avoid.

So this is a replication, not a new idea.  Either outcome is worth the
hour: it confirms the row and the row becomes citable, or it refutes it
and a four-point claim with no rig behind it comes out of the notes.
Whichever way it lands, commit the rig this time.

## 2. Simplify the histogram cut -- MEASURED 2026-11-10

`tab.yue:253-444` is 94 code lines in a sealed `do` block with three
module-level buffers (`Hist`, `ThisC`, `ThatC`).  Its job is one
sentence: of every (column, threshold) pair, return the one whose two
sides have the least size-weighted class entropy.  Seven
implementations were written and timed -- `tab-dev/attic/cutsimple/`,
figure `docs/cuttime.png`, raw timings in the session scratchpad as
`bench3-final.csv` (307 sets x 7 arms) and `bench3b.csv` (classify,
replicated).

| version | lines | globals | root cut | classify | regress | optimize |
|---|---|---|---|---|---|---|
| `tab.yue` as shipped | 94 | 3 | -- | 1.00x | 1.00x | 1.00x |
| `cut4` `Sym` per bin, fresh | 44 | 0 | 113/120 | 2.5-2.8x | 1.9x | 2.7x |
| `cut6` `Sym` per bin, reused | 61 | 0 | 113/120 | 1.6-2.0x | 1.2x | 2.0x |
| `cut10` dense, one sweep | 78 | 0 | **120/120** | 1.25-1.5x | 1.1x | 1.4x |
| `cut8` as cut10, per-column buffers | 79 | 0 | **120/120** | 1.3-1.6x | 1.2x | 1.4x |
| `cut5` the 94, per-column buffers | 96 | 0 | **120/120** | 0.98x | 1.00x | 1.02x |
| `cut9` the 94, one table-level buffer | 95 | 0 | **120/120** | 0.95x | 0.76x* | 0.98x |
| `cut11` the 94 + narrowed clear only | 96 | 3 | **120/120** | 0.96x | -- | -- |

Method: LuaJIT, `os.clock`, 3 reps, 5000-row cap, serial.  The ratio
is PAIRED (all arms run back to back on one set), which is what makes
it survive a box whose absolute times drift 31% median between runs.
classify was run twice; `cut9`/`cut5` replicate to 1%, the slower arms
move 16-23% in the median, so they are ranges.  (*) `cut9`'s 0.76x on
regression is ONE run and should not be quoted until replicated.

Three findings worth keeping:

- **The globals are free to remove.**  `cut11` keeps them and changes
  only the clear; `cut9` removes them and changes the clear.  Same
  speed.  So de-globaling costs nothing measurable and is pure taste.
  Put the buffers on the TABLE, not the column: `cut5` hangs them per
  column and loses to `cut9` everywhere, because one hot array beats
  279 cold ones.  Sizing is not the cost, locality is.

- **A 2-line win, independent of everything else.**  `tally` clears
  all `nb*nk` cells but reports `lo,up` and the sweep reads only that
  span, so cells outside it were already zero.  Clear the PREVIOUS
  call's span instead: exact (a cell outside every span has never been
  written), ~4% median, faster on 86 of 120 sets.  Most of a tree's
  nodes are small, and a four-row leaf pays the full 51*nk today.

- **44 lines and full speed is not available.**  `SYM.add` keeps `cl`
  current, which puts two `log` calls on the PER-ROW path; the 94
  moved all log arithmetic off that path into the per-bin sweep.
  `cut6` strips every allocation out of `cut4` and still only reaches
  1.6-2.0x.  The line count is buying the speed.

The flag-shaped seam, if one is wanted, is NOT 44+50 -- `cut4` and the
dense path share no code at all (`Sym` per bin vs one dense array), so
a flag over them ships ~106 lines and two copies that can drift.  The
real seam is the incremental `cl` carry: 17 lines, 1.25-1.5x, and it
is what forces two sweeps (NUM walks forward carrying a float, SYM
cannot).  Drop it and the sweeps merge into one local function that
writes nothing into tab's shared NUM and SYM -- that is `cut10`.

`cut4`'s 7 root-cut disagreements are all two-way ties on BINARY
symbolic columns (`surgery|no` vs `surgery|yes`, `is_recid|0` vs `1`,
`LEFT-WEIGHT` vs `RIGHT-WEIGHT` at the same threshold).  Those define
the identical partition; the tree is mirrored, not different.  OPEN:
the count is not stable run to run (112, 113, 114 seen), and that is
not explained.

Nothing here has been applied.  `tab.yue` is untouched.
