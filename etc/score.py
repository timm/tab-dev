#!/usr/bin/env python3
"""score.py: scores every arm shares, so the numbers compare.

Nothing here imports a learner.  That is the point: nn.py runs under
torch and lgbm.py under lightgbm, and loading the second one's libomp
into the first one's process segfaults torch while it builds a layer.
A dependency-free module is the only safe place for code both need.
"""

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

def aucs(model, X2, want):
  "Macro mean of each klass's one-against-the-rest auc, and its count."
  P  = model.predict_proba(X2)
  ks = [str(k) for k in model.classes_]
  out = [a for j, k in enumerate(ks)
         if (a := auc1([p[j] for p in P], [str(w) == k for w in want]))
            is not None]
  return f"{sum(out)/len(out):.4f},{len(out)}" if out else "0,0"
