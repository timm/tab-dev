#!/usr/bin/env python3
"""score.py: scores every arm shares, so the numbers compare.

Nothing here imports a learner.  That is the point: nn.py runs under
torch and lgbm.py under lightgbm, and loading the second one's libomp
into the first one's process segfaults torch while it builds a layer.
A dependency-free module is the only safe place for code both need.

Every score comes out twice, weighted by klass frequency and averaged
equally over klasses.  They answer different questions.  The weighted
one asks how a learner does on a row drawn from this data; the macro
one asks how it does on a klass drawn from this data's klasses.  Under
imbalance they part company hard: a rare klass the model never
predicts costs the macro mean its whole share and the weighted mean
almost nothing, which is how an auc of .999 came to sit beside a pd
of 30.  Both are written because a cached score cannot be re-scored
-- changing the metric means re-running every arm on every set -- so
the cheapest time to record the other average is while the first one
is being computed.
"""

def abcd(want, got):
  """Per-klass (tp, fp, fn, tn, support) keyed by str(klass), with the
  row count and the hit count.

  The keys come from `want`, not from `got`: a klass the model never
  predicts still has a recall of zero, and dropping it is exactly what
  would make a learner look better for ignoring the rare case.  A
  klass only `got` ever names has no support, so it raises some other
  klass's pf and gets no row of its own.
  """
  n, ok, ws, gs, hs = len(want), 0, {}, {}, {}
  for a, b in zip(want, got):
    a, b = str(a), str(b)        # a klass may be int here and str
    ok += a == b                 # there: sklearn coerces mixed columns
    ws[a] = ws.get(a, 0) + 1
    gs[b] = gs.get(b, 0) + 1
    if a == b: hs[a] = hs.get(a, 0) + 1
  out = {}
  for x in sorted(ws):           # sorted: float addition is not
    w  = ws[x]                   # associative, so the walk order is
    tp = hs.get(x, 0)            # part of the answer
    fp = gs.get(x, 0) - tp
    fn = w - tp
    out[x] = (tp, fp, fn, n - tp - fp - fn, w)
  return out, n, ok

Acc = "acc,pd,pf,d2h,macropd,macropf,macrod2h,klasses"

def macro(want, got):
  """`Acc`: accuracy, then pd, pf and d2h weighted by klass frequency,
  then the same three averaged equally over klasses.

  The klass count comes last, and the reader needs it: `fp + tn` is
  `N - n_k`, so it is zero exactly when every test row is klass k.
  That klass has no negatives, so there is no false alarm rate and no
  d2h built on one -- and since the guard can only fire for a klass
  that *is* the whole test set, no second klass survives it.  So the
  four pf and d2h columns of a one-klass split are written 0 and mean
  nothing; gate on `klasses > 1`.  Writing a real 0 there would score
  a measurement that does not exist as a flawless one.

  pd is accuracy.  Weighting recall by support gives
  sum_k (n_k/N)(tp_k/n_k) = sum_k tp_k / N, which is the hit rate --
  the two columns agree to the last digit by construction, not by
  accident of this data.  It is written anyway: `pd` then means one
  thing in every column of every chart, and the identity is on the
  page instead of in someone's head.
  """
  parts, n, ok = abcd(want, got)
  wpd = wpf = wd2h = mpd = mpf = md2h = 0.0
  for tp, fp, fn, tn, w in parts.values():
    r1 = tp / (tp + fn)
    wpd += w * r1; mpd += r1
    if fp + tn == 0: continue
    f1 = fp / (fp + tn)
    d1 = ((1 - r1) ** 2 + f1 ** 2) ** .5 / 2 ** .5
    wpf += w * f1; wd2h += w * d1
    mpf += f1;     md2h += d1
  k = len(parts)
  return (f"{100*ok/n:.1f},{100*wpd/n:.1f},{100*wpf/n:.1f},{wd2h/n:.3f},"
          f"{100*mpd/k:.1f},{100*mpf/k:.1f},{md2h/k:.3f},{k}")

def auc1(scores, wants):
  "Area under the roc curve, from the rank sum.  Ties share a place."
  t  = sorted(zip(scores, wants))
  np = sum(1 for _, w in t if w)
  nn = len(t) - np
  if not np or not nn: return None
  tot, j = 0.0, 0
  while j < len(t):
    k = j
    while k + 1 < len(t) and t[k + 1][0] == t[j][0]: k += 1
    r = (j + 1 + k + 1) / 2             # 1-based mean place of a tie
    tot += r * sum(1 for m in range(j, k + 1) if t[m][1])
    j = k + 1
  return (tot - np * (np + 1) / 2) / (np * nn)

Auc = "auc,klasses,macroauc"

def aucline(cols):
  """`Auc`: the frequency-weighted mean of each klass's
  one-against-the-rest auc, how many klasses had one, and the
  equally-weighted mean beside it.  `cols` is one (scores, wants) pair
  per klass.

  A klass with no positives or no negatives in this test split has no
  auc at all, so it is dropped and the weights renormalise over what
  is left -- `w`, not `len(want)`.  Giving a weight to a measurement
  that does not exist would be scoring a gap as if it were a result.
  """
  tot = w = 0.0
  mac = []
  for s, t in cols:
    a = auc1(s, t)
    if a is None: continue
    nk   = sum(1 for b in t if b)
    tot += nk * a
    w   += nk
    mac.append(a)
  if not mac: return "0,0,0"
  return f"{tot/w:.4f},{len(mac)},{sum(mac)/len(mac):.4f}"

def aucs(model, X2, want):
  "`Auc` for anything with sklearn's predict_proba and classes_."
  P  = model.predict_proba(X2)
  ks = [str(k) for k in model.classes_]
  return aucline([([p[j] for p in P], [str(w) == k for w in want])
                  for j, k in enumerate(ks)])

def aucposts(want, posts):
  "`Auc` from a list of p(klass|row) dicts, one per test row."
  ks = sorted({k for p in posts for k in p}, key=str)   # a klass may
  return aucline([([p.get(k, 0) for p in posts],        # be an int, so
                   [str(w) == str(k) for w in want])    # look it up as
                  for k in ks])                         # itself, compare
                                                        # as text
