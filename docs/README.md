# docs

`docs/rq.md` is the argument. The figures split two ways.

**Reproducible** -- `,/run figures` rebuilds these from `cache/`:

| figure | job | metric |
|--------|-----|--------|
| `clas.png`   | `charts.py clas`   | pd, pf, d2h on moot/classify |
| `labels.png` | `charts.py labels` | mae, with the effect-size tie test |
| `top5.png`   | `charts.py top5`   | rank |
| `secs.png`   | `charts.py secs`   | secs(LightGBM) / secs(arm) |
| `raw.png`    | `charts.py raw`    | absolute seconds, per task |
| `cost.png`   | `charts.py cost`   | seconds against rows |

All six read the `nb72` arm for classify and `rmeans` for regression,
so they describe one learner at tab's defaults (`bins=7, m=2`).

**Archival** -- kept because `rq.md` cites them, but nothing in this
repo redraws them. The plotting code was never committed:

| figure | what made it |
|--------|--------------|
| `hpo.png`, `bins.png` | the sweeps in `etc/hpo.lua` produce the numbers, but the chart that drew them is lost (added in lisp `54b9010` with no script) |
| `opt.png` | cited as "top five, multi-objective"; no producer found |
| `p.png` | not referenced by `rq.md` at all; an orphan |

`charts.py` also defines a `gain` job, which has no figure: it compares
the per-cluster arm `nbc` against `nb`, and `nbc` now exists only in
`attic/jiffy.lua`.
