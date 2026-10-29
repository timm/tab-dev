# attic

Code kept for provenance, not for use. Nothing here is on the path.

| file | why it is kept |
|------|----------------|
| `jiffy.lua` | tab's ancestor. The only implementation of the arms behind `cache/*/nb50.csv`, `nb72.csv` and `nbc.csv`: AODE, per-cluster naive Bayes (`TBL.cluster/spread/votes`), kNN, and the supervised binners (`NUM.cuts/chop/merge/pkid`). Delete this and 215 cached score files become unexplainable. |
| `jiffy-eg.lua` | its rig, 4.6K larger than `tab-eg.lua`; carries the extra arms and `BAG.abcd` per-class scoring |
| `min.lisp`, `min-eg.lisp` | the Common Lisp reference implementation `docs/rq.md` cites as printing exactly its worked six-row example |
| `Makefile` | retired by the move to `,/run`. Kept for its comments, which are the only record of the cache design: "Make invalidates; lua rebuilds", one stamp per language so editing lua never voids an hour of LightGBM runs, and why a dir named `,` can never appear in an a2ps path |

Knobs `jiffy.lua` had and `tab.lua` dropped: `w` (info-gain column
weighting), `parts`/`stop`/`enough` (the clustering trio), `sup` (mdl cuts,
equal count, merge up), `small`, `knn`, `per`, `pick`.
