# What commercial AI use costs (2026 figures)

For the paper's third beat: seek things we can understand (Rudin),
and refute (MSR'13), at budgets that don't gate who plays.

## Per employee, all industries (Ramp platform data)

Zohar Kharazian (Ramp economist) on Plain English with Derek
Thompson, 2026-10-23
(https://www.theringer.com/podcasts/plain-english-with-derek-thompson/2026/10/23/the-ai-story-wall-street-doesnt-want-to-hear):

> If you look at the median company on our platform, of businesses
> that spend on AI, they spend about $12 to $15 per employee per
> month on AI.  The top 10 percent company spends about $800 per
> employee per month.  And then the top 1 percent company spends
> upwards of $10,000 per employee per month on AI.

Three orders of magnitude between median and top 1%.  AI spend is
not just big; it is extremely concentrated (his framing: a product
and maybe a policy issue).

## Per developer, coding tools (2026 industry surveys)

- Anthropic enterprise figures for Claude Code: $150--250 per
  developer-month (~$13 per active day; 90% of users under $30 on
  any active day).
- All-in (seat + tokens), mixed inline/agentic teams: $200--600
  per developer-month.
- Agentic power users: $500--2,000/month; one 27-company survey:
  mean $248, 99th percentile $2,452.
  (getdx.com, morphllm.com, stackness.dev, tokenade.net, 2026.)

## The argument

Reproducibility has a price axis.  A method whose verification
needs top-1% spend ($10k/employee-month) can be checked by the top
1%.  This paper's method runs its fast loop on a laptop for
approximately $0/month, uses an LLM assistant at commodity rates
during design only, and ships an artifact whose re-verification
costs one download -- science at the median company's budget, not
the 99th percentile's.
