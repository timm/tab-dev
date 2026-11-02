# Horthy (HumanLayer): software factories and their failures

Two sources:
- Talk: "Harness engineering is not enough: why software factories
  fail" (AI.Engineer 2026),
  https://ai.engineer/talks/Ib5GBkD555M-harness-engineering-is-not-enough-why-software-factories-fail
- Video: "AI Agents Still Can't Maintain Your Codebase" (Perfology,
  2026), youtube ntO2eQ2iu6o.  Cites SlopCodeBench (see
  slopcodebench26.pdf -- Orlanski & Adila, UW-Madison).

**Core argument:** coding agents accelerate implementation but
degrade long-term maintainability without safeguards.  Passing
tests does not mean good software; "lights-off" factories hide
costs in production quality and future maintenance.  The fix is
moving human judgment *earlier* (planning, architecture review,
visual alignment), not eliminating it.

**Cited evidence:**
- Faros AI (2026): production incidents and bugs per developer rise
  during AI-adoption periods; more review comments and more
  unreviewed merges.
- SlopCodeBench: frontier agents 12.2--16.3% strict pass over
  iterative checkpoints; erosion in 80% of trajectories.
- Benchmark landscape: SWE-bench Multilingual (~15-min tasks),
  SWE-Marathon (400-hour tasks), DeepSWE, FrontierCode (multi-PR
  with quality judgments).

**For the tab paper:** Horthy's title names the obvious objection
to our loop -- "a harness is not enough" -- and his answer is also
ours: the human stays in the loop, early and cheap.  In our method
the harness (goldens, speed gate) freezes behavior, while the
human supplies taste and direction at ~11 words per prompt
(interrogate, reject, select).  tab is a one-author lab-scale
counterexample to lights-off factories, not an instance of them:
judgment was never removed, it was made cheap.
