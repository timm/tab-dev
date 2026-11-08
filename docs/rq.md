# rq: how simple can a learner be?

Three claims, one estimator, 244 lines of Common Lisp:

1. **Simple classifiers work fine.** Naive Bayes over binned
   columns lands within a point or three of LightGBM.
2. **Simple regression works fine.** The same bins, averaged by
   variance reduction (`rmeans`), tracks a gradient booster at a
   small constant factor -- and stops needing data at about a
   hundred labels.
3. **Simple optimisers built on that regression are fine.**
   Rank the unseen rows by the guess, pay for five labels, and
   two thirds of the time you hold a top-5% row.

None of this is new in kind -- the lineage runs from Holte's 1R
through discretized naive Bayes -- but it is measured here under
one protocol, in one small program, against a current booster.

## The code

`min.lisp` (244 lines) is the whole learner: csv reader, column
summaries, bins, `rmeans`, and the three statistical tests that
police the results.  `arms.lisp` (190) is the harness.  No
libraries: no numpy, no pandas, no ezr.  Runs on SBCL and CLISP,
which agree to the last digit on every number below.

## The rigs

*Classification* (`etc/nb60b17.tsv`, `etc/aode60b5.tsv`,
`etc/lgbm60.tsv` from the ezr repo).  60 `moot/classify` sets,
20 seeds, accuracy.

*Regression* (`arms.lisp -learn`, `-rank`).  60
`moot/regression` sets on the frozen 80:20 splits of
`etc/rcache.py`, 20 seeds, raw MAE on the held-out rows.  The
target is the raw `!` cell, so both arms are scored by identical
arithmetic.  LightGBM's predictions come from the cache; it
always reads every training row.

*Optimisation* (`arms.lisp -opt1`).  125 `moot/optimize` sets,
`y` = `ydist`, the distance to heaven over **all** goal columns.
Budget is ezr's own: `Stop=50`, `Check=5`, so 45 rows train the
model and 5 more pay to look at the top of its ranking.

Everything is the **median of 20 repeats**.  "Tied" means
`same`: Cohen's d <= 0.35 **and** Cliff's delta <= 0.195 **and**
Kolmogorov-Smirnov <= 1.36, all three agreeing.

## RQ1: do simple classifiers work?

![simple classifiers](docs/attic/clas.png)

| arm | wins | ties | losses | median accuracy |
|---|---|---|---|---|
| naive Bayes | 9 | 11 | 40 | 81.5% |
| AODE | 13 | 11 | 36 | 82.8% |
| LightGBM | -- | -- | -- | 85.3% |

- **LightGBM wins more often, by very little.**  The median
  accuracy gap is **3.3 points** for naive Bayes and **1.4** for
  AODE.  Counting wins makes the booster look dominant; the
  profile shows two curves a hair apart.
- **Tied or better on 20 of 60** (naive Bayes) and **24 of 60**
  (AODE).  Relaxing independence a little -- AODE's one-level
  dependence -- recovers nearly half the remaining gap.
- The curves only separate at the hard end.  Where LightGBM is
  above 95% the simple learners are too.

## RQ2: do simple regressors work?

![labels vs error](docs/attic/labels.png)

`rmeans`, raw MAE, against LightGBM reading all of the 80%:

| rmeans trained on | better | tied | worse |
|---|---|---|---|
| 50 labels | 13 | 9 | 38 |
| every row of the 80% | 17 | 10 | 33 |

- **Not worse on 22 of 60 sets** at fifty labels.  Median raw
  MAE 5.41 (50 labels), 5.36 (all), 2.43 (LightGBM).
- **More labels stop helping at about a hundred.**  `2dplanes`
  goes 2.90 -> 2.71 -> 2.68 for 25 -> 100 -> *32,614* rows;
  `autompg` 3.87 -> 3.21 -> 3.07.  A 300x increase in data buys
  single digits.  The remaining gap is structural -- one mean
  per bin per column cannot see interactions -- so there is
  nothing to buy with more labels.
- **Where it wins, it wins small.**  The thirteen wins are
  nearly all under 250 training rows, where 100 boosted trees
  overfit and a grand-mean-shrunk column average does not.

## RQ3: do simple optimisers work?

Ranking is an easier question than prediction: get the *order*
right and the values can be wrong.

![top five, regression](docs/attic/top5.png)

*One target, 60 regression sets.*  Rank the held-out rows by the
guess, label the top five, keep the best of those.  The y axis
is that row's rank as a percent of the test set.

- **50 of 60 inside the top 5%** on a budget of 50, against 49
  of 60 reading every row.  **29 of 60** return the actual best
  row in the test set.  On this corpus the frugal arm is already
  at the ceiling.
- **Ranking survives where prediction fails.**  `2dplanes` has a
  terrible MAE (2.90 against 0.80) and still puts a top-1.8% row
  in its first five picks.

![top five, multi-objective](docs/attic/opt.png)

*Every goal at once, 125 optimize sets.*  Same protocol, `y` =
distance to heaven over all goals.

- **81 of 125 inside the top 5%** on 45+5, **98 of 125** reading
  every row; the best row outright on 15.
- **Size does not break it.**  `javagc` has 33,395 test rows:
  6.45% on fifty labels, 0.87% reading all of them.
- **More labels is not monotone.**  The all-labels arm is better
  on aggregate yet *worse* than the 45-label arm on **48 of
  125** sets, sometimes 28% against 1%.  The m-estimate explains
  it: at 45 rows the pull toward the grand mean is strong, so
  the ranking is conservative and rarely catastrophic; with
  every row the shrinkage vanishes and one confidently wrong bin
  mean can push a bad row to the top.  Sharper estimates, no
  safety net.

## Is there anything to tune?

![m-estimate sweep](docs/attic/hpo.png)

The estimator has one free parameter: `m`, the prior weight that
pulls a bin mean toward the grand mean.  A sweep over
m = 0, 1, 2, 4 across the 125 `moot/optimize` sets, at label
budgets of 25, 50, 100, 200 and 400, medians of 20 seeds
(`luajit hpo.lua file=...`).  The score is the RQ3 score: where
the best of the top five guesses really ranks, as a percent of
the test rows.

| labels | sets | m=0 | m=1 | m=2 | m=4 |
|---|---|---|---|---|---|
| 25 | 125 | 3.91 | 3.92 | 3.92 | 3.60 |
| 50 | 125 | 2.83 | 2.90 | 2.68 | 3.00 |
| 100 | 123 | 2.62 | 2.90 | 2.87 | 2.87 |
| 200 | 112 | 2.23 | 1.94 | 1.91 | 2.02 |
| 400 | 108 | 1.40 | 1.34 | 1.20 | 1.30 |

A budget is only run where the training split holds that many
rows, hence the falling set counts.

- **Nothing to tune.**  At every budget, each of m = 0, 1, 4 is
  indistinguishable from the default m = 2: Cohen's d, Cliff's
  delta and the KS test all agree, all five times.  Counting
  which m wins each (set, budget) pair gives 358 / 353 / 355 /
  365 -- a four-way tie.  Paired against m = 2, the median
  difference is exactly zero for all three rivals, and the mean
  differences are under 0.03 points.
- **Per data set, the same story.**  The figure sweeps `m` at
  fifty labels, one point per set, with the sets sorted by the
  default m = 2 so that baseline runs as a smooth curve and any
  rival that strayed would show up as a spike.  On **107 of
  125** sets (the gray bands) all four values of `m` are
  indistinguishable over 20 seeds; the median spread between
  the best and the worst `m` is 0.44 points, and only a handful
  of sets on the right reach one point or more.
- **The knob is smaller than the noise.**  The four curves lie
  within 0.4 points of each other; the spread *between* data
  sets at the same budget is ten times wider -- at 25 labels the
  middle half of the sets runs 1.5% to 7.4%.  Hyper-parameter
  optimisation here would be fitting seed noise.
- **Labels are the knob that matters.**  Going 25 -> 400 labels
  moves the median from 3.9% to 1.2%, and the useful part of
  that move is early: 25 -> 50 buys more than 200 -> 400.
  Deleting the m-estimate altogether (m = 0) costs nothing
  measurable, so the shrinkage earns its place as insurance on
  thin bins rather than as a tuned quantity.

The second knob is `bins`, how many slices a numeric column is
cut into.  Same rig, `m` held at 2:

![bins sweep](docs/attic/bins.png)

| labels | sets | bins=3 | bins=5 | bins=7 | bins=9 | bins=11 |
|---|---|---|---|---|---|---|
| 25 | 125 | 4.16 | 3.92 | 3.77 | 4.35 | 3.85 |
| 50 | 125 | 3.24 | 2.68 | 2.98 | 2.93 | 3.12 |
| 100 | 123 | 2.62 | 2.87 | 2.90 | 2.90 | 3.08 |
| 200 | 112 | 2.12 | 1.91 | 1.79 | 1.47 | 1.64 |
| 400 | 108 | 1.30 | 1.20 | 1.06 | 1.27 | 1.19 |

- **`bins` bites harder than `m`, and still does not pick a
  winner.**  Every setting is indistinguishable from the default
  `bins=5` at every budget, the paired median difference is
  again exactly zero, and the win counts (303 / 304 / 314 / 322 /
  327) spread over five choices the way chance would.  No
  setting is best at more than two of the five budgets.
- **The disagreement is per data set, not per setting.**  At
  fifty labels only **69 of 125** sets tie across all five
  values of `bins`, against 107 for `m`, and the median
  best-worst spread is 1.53 points against 0.44.  Sorting the
  sets by `bins=5` turns that baseline into a smooth curve and
  the rivals into scatter around it -- scatter in both
  directions, with no setting riding above or below for long.
  Each set has a bin count it happens to like; nothing says in
  advance which, and the sets that care sit at the right of the
  figure, where every setting already scores badly.

## Does splitting first help a naive Bayes?

![tree](docs/attic/tree.png)

A binary tree grown on klass entropy -- the same cut search as the
regression tree, with `Sym` collecting the scores so `div` is
entropy rather than sd -- with a naive Bayes fitted inside each
leaf.  Depth scales with the klass count, so the tree always has at
least one leaf per klass; at a fixed depth of 4 a majority vote
over 8 leaves cannot name soybean's 19 klasses, and would be
reporting the shape of the tree rather than what it learned.  Both
arms share one tree per split, so the only thing that differs is
the answer given at the leaf.  72 `moot/classify` sets.

| arm | pd | pf | auc | ahead of nb on auc |
|---|---|---|---|---|
| naive Bayes | **73.0** | **13.8** | **0.869** | -- |
| tree, NB at the leaf | 70.9 | 15.0 | 0.848 | 27 of 72 |

- **Splitting first does not pay.**  The tree loses on every
  measure and in every klass band, worst at 6+ klasses (auc 0.869
  against 0.902, ahead on 6 of 21), which is where the scaled
  depth leaves each leaf the fewest rows.
- **Majority-at-the-leaf is worse still** (auc 0.778): the tree can
  locate a region but cannot label it.  Whatever a split buys, it
  needs a model to collect.
- It pays in one place.  `car`, `nursery`, `balance.scale`,
  `tic-tac-toe` and `kr.vs.kp` define their klass by a rule over
  several columns at once -- a torque comparison, a win condition,
  a chess endgame -- and there the tree gains **+7.8 pd** over
  naive Bayes against **-2.0** everywhere else.  The split buys
  exactly the thing an additive model cannot represent, and
  nothing else.

## How far behind is a naive Bayes?

![arms](docs/attic/arms.png)

The same three panels against a gradient booster and a foundation
model, on the 67 sets all three completed.

| arm | pd | pf | auc | ahead of nb on auc |
|---|---|---|---|---|
| naive Bayes | 74.5 | 14.1 | 0.872 | -- |
| LightGBM | 76.1 | 14.1 | 0.868 | 35 of 67 |
| TabICLv2 | **81.2** | **11.6** | **0.908** | 57 of 67 |

- naive Bayes and LightGBM are a tie -- 0.872 against 0.868, and
  LightGBM ahead on 35 of 67, which is a coin toss.  The whole of
  the deficit sits in the 3-5 klass band (0.872 against 0.889); at
  two klasses naive Bayes is *ahead* (0.846 against 0.826).
- TabICL leads, with 48 separated wins and 4 separated losses once
  `SAME` sets the one-sample cases aside.  It buys more on pf than
  on pd: fewer false alarms rather than more hits.

## Can we say in advance where a simple learner fails?

Red on the x axes of both figures marks the sets where the two
arms being compared part by at least 10 pd points: 11 sets in the
tree figure, 19 in the rival figure.  The rule is computed, not
chosen, so the marks mean one definite thing.

Nothing about the shape of those 19 sets predicts that they are
the ones to part:

| property | red | rest | cliffs |
|---|---|---|---|
| rows | 625 | 345 | +0.12 |
| x columns | 12 | 18.5 | -0.22 |
| symbolic fraction | 0.74 | 0.75 | +0.01 |
| klasses | 3 | 2 | +0.15 |
| majority klass share | 0.52 | 0.57 | -0.15 |
| **synergy** | **-0.0014** | **-0.0123** | **+0.48** |

The last row is the only one that moves, and it is the only
measure here that is a statement about naive Bayes's own
assumption rather than about the data's shape.  **Synergy** -- how
much a pair of attributes says about the klass that neither says
alone, $I(X_i,X_j;Y) - I(X_i;Y) - I(X_j;Y)$, normalized by $H(Y)$
and with its permutation null subtracted -- is information only a
model that reads the pair together can reach, and so is exactly
what an additive learner must discard.

Most sets have *negative* synergy: their columns repeat each
other, and that is the regime where naive Bayes does fine, because
double-counting redundant evidence leaves the ranking intact.  The
sets that part the arms are the ones that are not redundant.
`car`, `nursery`, `balance.scale`, `tic-tac-toe` and `kr.vs.kp`
all define their klass by a rule over several columns at once -- a
torque comparison, a win condition, a chess endgame -- and there
the tree gains **+7.8 pd** over naive Bayes against **-2.0**
everywhere else.

Asked a different way, though, synergy is much weaker.  Drop the
red/rest split and regress it against a continuous outcome -- the
best rival's auc minus naive Bayes's, over all 67 sets, with no
grouping anywhere:

| framing | synergy |
|---|---|
| red against rest, cliffs | +0.48 |
| against best-rival-minus-nb auc, spearman | +0.29 |

Both are honest and they are not in conflict: cliffs compares the
extremes, spearman tracks the whole range.  **Synergy separates
the ends and barely orders the middle.**  Every shape property
stays near zero under the continuous framing too (rows +0.14,
symbolic fraction -0.20, the rest under 0.12), so synergy remains
the best predictor found.

The negative result is what survives:

- **No property of a dataset's shape predicts whether simple will
  do.**  Size, width, klass count, symbolic fraction and imbalance
  all fail, under either framing.
- **Synergy tells you about the extremes only.**  It is measured
  pairwise, so it understates targets like `tic-tac-toe` whose
  rule is a three-way conjunction; and it leaves `anneal`,
  `hypothyroid`, `page.blocks` and `waveform5000` unexplained --
  those sets part the arms because the arms are unstable, not
  because naive Bayes is structurally beaten.
- So there are two causes with one symptom, and only the extreme
  cases of one of them are readable off a csv.  A wide spread
  between arms does not tell you which cause you have.  The advice
  this document keeps arriving at stands: run the cheap learner,
  and keep the rig that tells you when it was not enough.

## When are 45 labels enough?

The section above found no property of a data set's *shape* that
says whether a simple classifier will do.  Asked of optimisation
and regression, and allowed to look at the *labels* rather than
the shape, the answer changes.

Across the 187 sets the win figures draw, the arms split into two
populations, and the separator is a property of the 45 labelled y
values themselves: **(mu-lo)/sd**, how far their mean sits above
the best of them, in units of their spread.  Below 2.25 (n=114),
`acquire` reaches a median win of **98** -- within two points of
LightGBM trained on every row.  Above 2.25 (n=73) it falls to
**72**.

What fails above that line is the budget, not the method:

| arm | (mu-lo)/sd <= 2.25 | > 2.25 |
|---|---|---|
| acquire, 45 labels | 98 | **72** |
| 45 random labels | 97.5 | 71 |
| forest(30), 45 labels | 98 | 75 |
| LightGBM, 45 labels | 92.5 | 63.5 |
| forest(30), every row | 99 | **100** |
| LightGBM | 100 | **100** |

Every 45-label arm collapses together above the line, and
forest(30) against `acquire` there is 29 wins to 28 -- a coin
flip.  Both every-row arms stay pinned at 100.  The information is
in the data; forty-five labels cannot reach it when the best row
is an isolated outlier rather than one of a population of good
ones.  This also locates LightGBM's advantage: against `acquire`
it takes 55 of 57 decided sets above the line but only 59 of 72
below it, so its lead sits almost entirely where the budget, not
the learner, is binding.

So the rule this yields is a **stopping rule, not a
model-selection rule**.  Having spent 45 labels one already holds
the 45 y values, so (mu-lo)/sd costs nothing further.  Low: the
budget has done its work and more labels will buy little.  High:
no change of acquisition strategy or learner will help, and the
honest choices are to collect more labels or to report that the
top five candidates will close about 70% of the available gap
rather than all of it.

Two checks the threshold survives.  It is not a disguised
sample-size effect -- within fixed row bands it still separates
the populations (cliffs 0.82 for 500-5000 rows, 0.64 above 5000),
and the observed values sit well under the `sqrt(2 ln n)` expected
of the minimum of n samples.  And it runs against its own
confound: `(mu-lo)` is the denominator of the win measure, so
mechanically a larger value *inflates* win for a fixed gap, the
opposite of what is seen.

Two shape properties do move here, where none moved for
classification, and both restate the budget rather than the
learner.  On optimize, easy sets carry a median of 2 goals against
3 (cliffs 0.49) -- readable off the header before any label is
spent.  On regression the split is row count, 189 against 8190
(cliffs 0.64), which is the label fraction in other words: 45 of
189 is 24% of the data, 45 of 8190 is 0.5%.

## What it costs

![seconds](docs/attic/secs.png)

The same estimator, five ways: `min.py` under CPython and pypy,
`jiffy.lua` under Lua and LuaJIT, `min.lisp` under SBCL.  Each
trains on the budget then scores every test row -- what the
protocol actually costs -- against LightGBM fitting all training
rows and predicting the test (one model per goal column).  124
optimize sets, mean of 3 seeds, model only, no parsing.

| data | rows | cpython | pypy | lua | luajit | sbcl | lgbm |
|---|---|---|---|---|---|---|---|
| player_statistics_cleane | 81 | 0.0033 | 0.0167 | 0.0008 | 0.0010 | 0.0019 | 0.09 |
| nasa93dem | 93 | 0.0029 | 0.0169 | 0.0015 | 0.0008 | 0.0021 | 0.36 |
| FM-500-100-0.50-SAT-1 | 10000 | 0.3195 | 0.0754 | 0.1007 | 0.0176 | 0.4648 | 3.96 |
| xomo_osp2 | 10000 | 0.0409 | 0.0239 | 0.0179 | 0.0019 | 0.0636 | 6.12 |
| Scrum100k | 100000 | 0.5768 | 0.0645 | 0.1506 | 0.0160 | 0.7987 | 5.83 |
| javagc | 166975 | 0.5841 | 0.0575 | 0.2015 | 0.0209 | 0.5893 | 1.91 |
| **total, 124 sets** | | **5.80** | **2.73** | **1.91** | **0.36** | **7.90** | **372** |
| **median speedup** | | **346x** | **163x** | **1,030x** | **2,430x** | **249x** | 1x |

- **Every runtime beats LightGBM by two to three orders of
  magnitude**, and no curve ever reaches parity.  The slowest of
  the five still has a median 163x.
- **LuaJIT wins outright**: 0.36s to LightGBM's 372s over the
  whole corpus, a median 2,430x.  Plain Lua is second (1,030x),
  and beats both Pythons.
- **pypy has a floor.**  Its JIT needs about 13ms of warmup,
  which is longer than most of these runs take, so it is the
  *slowest* arm by median despite winning on the widest tables.
- **SBCL's total is dragged by wide tables.**  Two 500- and
  1,044-column SAT sets cost it 1.46s of its 7.90s: `guess`
  walks the columns with a hash lookup each, and that constant
  shows when there are a thousand of them.
- The spread between runtimes (0.36s to 7.90s) is smaller than
  the gap to LightGBM (372s).  Which language you pick matters
  far less than which algorithm.

## The estimator, in full

Four steps, no iteration.

*1. Bin.*  A numeric column is cut on the logistic norm of its
z-score, clipped at three standard deviations, into $B=5$ bins:

$$z = \max(-3, \min(3, (v - \mu_c) / \sigma_c)), \qquad
\Phi(z) = \frac{1}{1 + e^{-1.7 z}}, \qquad
b_c(v) = \min(B, 1 + \lfloor B \Phi(z) \rfloor)$$

A symbolic column is its own bin: $b_c(v)=v$.  $\mu_c,\sigma_c$
come from the **training** rows only.

*2. Collect.*  One pass: for every x column $c$ and bin $b$, the
count $n_{cb}$ and mean $\bar y_{cb}$ of the training rows that
land there; and over all of them the grand $n$, $\bar y$,
$\sigma$.

*3. Shrink.*  A bin's mean is pulled toward the grand mean by an
m-estimate ($m=2$), so a thin bin cannot invent a prediction:

$$\hat y_{cb} = \frac{n_{cb} \bar y_{cb} + m \bar y}{n_{cb} + m}$$

*4. Weight and average.*  Each column is worth how much variance
its bins remove -- CART's split criterion, k-way -- and the
guess is the weighted mean of its bins' shrunken means:

$$w_c = \max\left(0, \sigma^2 - \sum_b
\frac{n_{cb}}{n} \sigma_{cb}^2\right), \qquad
\hat y(r) = \frac{\sum_c w_c \hat y_{c, b_c(r)}}{\sum_c w_c}$$

with $\bar y$ returned when no column has both a known bin and
$w_c>0$.

```
train(rows, y):                     guess(r):
  all = Num(y(r) for r in rows)       s = w = 0
  for each x column c:                for each x column c:
    for each row r:                     v = bins[c][bin(c, r[c])]
      add y(r) to                       if v and w[c] > 0:
        bins[c][bin(c, r[c])]             s += w[c] * est(v, all)
    w[c] = vcut(bins[c], all)             w += w[c]
                                      return w>0 ? s/w : all.mu
```

### A six-row example

Columns `Age` (numeric), `job` (symbolic), goal `Cost-`:

| Age | job | Cost- |
|---|---|---|
| 1 | a | 10 |
| 2 | a | 12 |
| 3 | a | 11 |
| 7 | b | 30 |
| 8 | b | 31 |
| 9 | b | 29 |

Grand: $n=6$, $\bar y=20.5$, $\sigma=10.445$.  `Age` has
$\mu=5,\sigma=3.406$, so 1 and 2 fall in bin 1, 3 in bin 2, 7 in
bin 4, 8 and 9 in bin 5.  Then:

| column | bin | $n_{cb}$ | $\bar y_{cb}$ | $\hat y_{cb}$ | $w_c$ |
|---|---|---|---|---|---|
| job | a | 3 | 11 | 14.80 | 108.10 |
| job | b | 3 | 30 | 26.20 | 108.10 |
| Age | 1 | 2 | 11 | 15.75 | 107.77 |
| Age | 2 | 1 | 11 | 17.33 | 107.77 |
| Age | 4 | 1 | 30 | 23.67 | 107.77 |
| Age | 5 | 2 | 30 | 25.25 | 107.77 |

A new row `Age=8, job=b` lands in `Age` bin 5 and `job` bin b:

$$\hat y = \frac{107.77 \times 25.25 + 108.10 \times 26.20}
{107.77 + 108.10} = 25.73$$

against a true neighbourhood of 29-31.  The m-estimate is
deliberately pulling toward 20.5, and with three rows per bin it
has not let go yet.  `min.lisp` prints exactly these numbers.

## Where this came from

The estimator is not new.  `(n·mean + m·prior)/(n + m)` is
Cestnik's m-estimate (ECAI 1990); for a numeric target grouped
by a category it is target encoding with smoothing
(Micci-Barreca, SIGKDD Explorations 3(1), 2001), which is
empirical-Bayes shrinkage.  Averaging per-column binned means is
an additive model over discretized univariates -- Holte's 1R
generalised from "pick the best column" to "average them all",
and the regression analogue of discretized naive Bayes (Frank et
al., *Naive Bayes for Regression*, MLJ 41, 2000).  Weighting by
variance reduction is CART's split criterion reused as a filter.

What is measured here is the *packaging*: those three pieces, at
a fifty-label budget, in 244 lines, against a current booster.

## Reproducibility notes

1. An early version of this rig binned test rows with columns
   summarised over **all** the training data while training on a
   sample, leaking the full x distribution into every
   small-sample condition and flattening the label curve by
   construction.  The model now carries its own columns; every
   number above is post-fix.
2. The regression corpus is 60, not 61:
   `moot/regression/delta.ailerons.csv` has a comma header and
   space-separated rows and was repaired outside the repo before
   caching; `delta.elevators.csv` has the same defect and is
   still excluded.
3. The optimize corpus is 125 -- `moot/optimize/*/*.csv` minus
   the two under `test/`.
4. `ezr.py` does not import at `537ee93` (`mid()` lost a line
   continuation), so `rcache.py` ran from a patched copy.
5. A split whose test rows all share one klass leaves every
   one-against-the-rest with no negatives, so there is no auc to
   report.  Both `score.py` and `tab-eg.lua` write `0,0` there,
   a zero klass count being the sentinel, and an early version
   of `charts.py` averaged that zero as if it were a score.  Six
   sets were affected -- `shuttle.landing.control` (17 of 20
   reps), `trains` (9), `weather` (7), `solar.flare2` (5),
   `solar.flare1` (4), `sponge` (4) -- and every arm equally,
   since the splits are shared.  It cost `shuttle.landing.control`
   0.500 auc, read as 0.075, and inflated the pooled sd strip by
   29% of its total height.  `charts.py` now reads auc only from
   reps with a nonzero klass count; `auc.png` was never affected,
   since its drop rule already required one.  Every number in
   this section is post-fix.
6. Timings are SBCL against Python calling a C++ library, so
   some of LightGBM's floor is marshalling, not tree building.
   The ezr repo's own `etc/arms.tsv` shows the same shape from a
   different harness (0.571s against 0.024s).
