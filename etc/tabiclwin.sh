#!/usr/bin/env bash
# tabiclwin.sh: give every-row TabICL a `win` column on every set.
#
# usage: etc/tabiclwin.sh todo.txt      (one moot csv per line)
#
# tabicl.csv on most regression and optimize sets was written before
# `win` existed, and thirteen optimize ones before the goal() patch
# (STALE-tabicl.txt), so a win figure could draw every-row TabICL on
# 26 of 57 regression sets and 19 of 96 optimize ones.  This reruns
# nn.py on the rest, FORCE=1, 20 reps like every other arm.
#
# Two workers and OMP_NUM_THREADS=2, as ,/run does it: the model holds
# its training set in memory, and four at once is how mnist_1 filled
# 32GB of swap.  nn.py writes a set's file only when all its reps are
# done, so a run killed part way leaves the old file as it was.
#
# The list is expected smallest job first: 91 of 121 sets are a quarter
# of the work, so most of a figure is drawable long before the end.
# Seconds from this run are NOT for a runtime figure -- two workers,
# two threads each.  etc/secs.py is the rig for that.
cd "$(dirname "$0")/.." || exit 1
export CACHE="$PWD/cache" FORCE=1 OMP_NUM_THREADS=2
NN=${NN:-$HOME/tmp/nnenv/bin/python}
xargs -P "${NNP:-2}" -S 8192 -I{} "$NN" etc/nn.py tabicl {} < "$1"
echo "tabiclwin: finished $(date)"
