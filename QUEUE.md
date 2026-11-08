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
