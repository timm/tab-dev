#!/usr/bin/env python3
"""tab.py: minimal tab.lua -- just rmeans regression + naive bayes.
Columns: Uppercase=Num, else Sym; names ending X skip, -+! are goals,
! is the klass, - means minimize. (c) 2026 Tim Menzies, MIT."""
import sys, os
from math import exp, log

the = dict(bins=7, m=2, p=2)

def thing(s):
  s = s.strip()
  try: return int(s)
  except ValueError:
    try: return float(s)
    except ValueError: return s

def logfmt(_indent=0, **d):                  # k=v ...; a dict value indents +1
  pad = "  " * _indent
  flat = " ".join(f"{k}={v}" for k, v in d.items() if not isinstance(v, dict))
  lines = [pad + flat] if flat else []
  for v in d.values():
    if isinstance(v, dict): lines.append(logfmt(_indent + 1, **v))
  return "\n".join(lines)

def csv(file):
  if file.startswith("~"): file = os.environ.get("HOME", "~") + file[1:]
  rows = []
  for line in open(file):
    s = line.strip()
    if s and s[0] != "#": rows.append([thing(v) for v in s.split(",")])
  return rows

class Num:
  def __init__(i, txt="N", at=0):
    i.txt, i.at, i.n, i.mu, i.m2 = txt, at, 0, 0.0, 0.0
    i.w = 0 if txt.endswith("-") else 1
  def add(i, v):
    if v == "?": return v
    i.n += 1; d = v - i.mu; i.mu += d / i.n; i.m2 += d * (v - i.mu); return v
  def div(i): return 0 if i.n < 2 else (max(i.m2, 0) / (i.n - 1)) ** .5
  def norm(i, v):
    if v == "?": return v
    z = (v - i.mu) / (i.div() + 1e-32)
    return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))
  def bin(i, v):
    return v if v == "?" else min(the["bins"], 1 + int(the["bins"] * i.norm(v)))

class Sym:
  def __init__(i, txt="S", at=0):
    i.txt, i.at, i.n, i.has = txt, at, 0, {}
    i.w = 0 if txt.endswith("-") else 1
  def add(i, v):
    if v != "?": i.n += 1; i.has[v] = i.has.get(v, 0) + 1
    return v
  def norm(i, v): return v
  def bin(i, v): return v
  def nVals(i): return max(2, len(i.has))

class Tab:
  def __init__(i, src):
    i.rows, i.cols = [], None
    for row in (csv(src) if isinstance(src, str) else src): i.add(row)
  def add(i, row):
    if i.cols is None: return i.head(row)
    i.rows.append(row)
    for col in i.cols: col.add(row[col.at])
    return row
  def head(i, names):
    i.names, i.cols, i.x, i.y, i.klass = names, [], [], [], None
    for at, txt in enumerate(names):
      col = (Num if txt[0].isupper() else Sym)(txt, at)
      i.cols.append(col)
      if txt.endswith("X"): pass
      elif txt[-1] in "-+!":
        i.y.append(col)
        if txt.endswith("!"): i.klass = col
      else: i.x.append(col)
  def clone(i, rows=None, how=None):
    out = [[c.txt.lower() for c in i.cols] if how else i.names]
    for row in (rows or []):
      out.append([getattr(c, how)(row[c.at]) for c in i.cols] if how else row)
    return Tab(out)
  def ydist(i, row):
    d = sum(abs(c.norm(row[c.at]) - c.w) ** the["p"] for c in i.y) / len(i.y)
    return d ** (1 / the["p"])

class Rmeans:
  "Regression: per-x-column bin means of y, m-estimated, weighed by variance."
  def __init__(i, tab, rows, y):
    sub = tab.clone(rows)
    i.all, i.cols, i.has = Num(), sub.x, {}
    for r in sub.rows: i.all.add(y(r))
    for col in sub.x:
      bins = {}
      for r in sub.rows: bins.setdefault(col.bin(r[col.at]), Num()).add(y(r))
      cut = i.all.div() ** 2 - sum(v.n / i.all.n * v.div() ** 2 for v in bins.values())
      i.has[col.at] = (bins, max(cut, 0))
  def guess(i, row):
    s = w = 0
    for col in i.cols:
      bins, wt = i.has[col.at]
      v = bins.get(col.bin(row[col.at]))
      if v and wt > 0:
        s += wt * (v.n * v.mu + the["m"] * i.all.mu) / (v.n + the["m"]); w += wt
    return s / w if w > 0 else i.all.mu

class Nb:
  "Naive Bayes: one sub-table per klass; guess the likeliest (binned data)."
  def __init__(i, tab, rows):
    i.tab, i.subs, i.n, i.nKlass = tab, {}, len(rows), 0
    for r in rows:
      v = r[tab.klass.at]
      if v not in i.subs: i.subs[v] = tab.clone(); i.nKlass += 1
      i.subs[v].add(r)
  def like(i, sub, row):
    m = the["m"]
    L = log((len(sub.rows) + m) / (i.n + m * i.nKlass))
    for j, col1 in enumerate(sub.x):
      v = row[col1.at]
      if v != "?":
        L += log((col1.has.get(v, 0) + m) / (col1.n + m * i.tab.x[j].nVals()))
    return L
  def guess(i, row):
    return max(i.subs, key=lambda k: i.like(i.subs[k], row))

if __name__ == "__main__":
  # naive bayes on a toy table (binned so every x is symbolic)
  t = Tab([["Age", "job", "klass!"],
           [20, "low", "no"], [22, "low", "no"], [25, "low", "no"],
           [30, "med", "no"], [60, "hi", "yes"], [62, "hi", "yes"],
           [65, "med", "yes"], [70, "hi", "yes"]])
  b = t.clone(t.rows, "bin")
  nb = Nb(b, b.rows)
  print("nb", nb.guess(b.rows[0]), nb.guess(b.rows[-1]))  # -> no yes
  # rmeans regression on a csv (target = distance-to-heaven over goals)
  if len(sys.argv) > 1:
    t = Tab(sys.argv[1])
    m = Rmeans(t, t.rows[:45], t.ydist)
    print("rmeans", round(m.all.mu, 3), round(m.guess(t.rows[0]), 3))
