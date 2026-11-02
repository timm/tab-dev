# The AI-acceleration backlash (evidence file)

The measured case that AI-assisted *delivery speed* is partly
illusory -- which is the tab paper's opening move: we never
optimized for delivery speed at all.

## The headline RCT

**METR 2025** (metr25slower.pdf, arXiv 2507.09089): randomized
controlled trial, 16 experienced open-source devs, 246 real issues
on their own repos.  With AI tools they were **19% slower** (CI +2%
to +39%, significant) -- while *believing* they were 20% faster.
Perceived acceleration, measured deceleration.

Caveat for honest citation: METR's February 2026 follow-up flipped
the point estimates (returning devs ~18% faster, new devs ~4%
faster) but neither is significant (CIs cross zero), and METR
itself calls that data unreliable: 30-50% of participants declined
no-AI tasks (selection on the measured dimension), pay changed
$150 to $50/hr, concurrent agents muddied timing.  So: 2025 result
not overturned, question unresolved; 2025 remains the only
significant RCT.  (https://metr.org 2025-07-10 post; 2026-02
update; see ingenire.com/blog/metr-2026-developer-productivity-study.)

## Longitudinal code-quality data

**GitClear** (211M changed lines, 2020-2024): code duplication up
4x; refactoring collapsed from ~25% to under 10% of changes;
churn nearly doubled; copy-pasted lines now exceed refactored
lines for the first time.

**DORA 2024** (Google): AI adoption lifts self-reported individual
productivity but correlates with a dip in delivery throughput and
a larger dip in delivery stability.

**Faros AI 2026, "The Acceleration Whiplash"** (faros26whiplash.pdf;
telemetry, 22,000 devs / 4,000+ teams over two years, low- vs
high-AI-adoption periods within each org): task throughput per dev
+33.7%, epics +66.2% -- but incidents per PR +242.7%, monthly
incidents +57.9%, bugs per PR +28.7%, and 31.3% more PRs merged
with no human review (reviewers can't keep pace).  Speed up, quality
down, oversight down: the whiplash.

**techdebt25productivity.pdf** (arXiv 2510.10165): AI-assisted
programming decreases experienced developers' productivity by
increasing technical debt and maintenance burden.

See also: slopcodebench26.pdf (agent code erodes over iterations),
sawada26agentmaint.pdf / pan26agentmaint.pdf (maintenance costs of
agent code), horthy.md (practitioner synthesis).

## For the tab paper

The backlash literature attacks "AI makes delivery faster".  tab
sidesteps: delivery speed was never the objective (zero of 868
logged prompts asked for it).  The same tools, pointed at veracity
instead of velocity -- with goldens freezing behavior and the human
supplying taste -- produced an artifact that *shrank* while its
behavior held.  The backlash is evidence that the commercial
objective function is wrong for science, not that the tools are.
