# Hand, Classifier Technology and the Illusion of Progress

Statistical Science 2006, 21(1):1--15.
pdf: hand06illusion.pdf (arXiv https://arxiv.org/pdf/math/0606441;
published version via Project Euclid).

**Core argument:** the perceived superiority of complex, modern
classification methods (neural networks, support vector machines)
over older, simple techniques (linear discriminant analysis, 1R)
is largely an illusion.

- **Diminishing marginal returns.** Simple models typically capture
  85--90% of the total achievable predictive accuracy; complex
  models add only tiny, often statistically or practically
  negligible, error-rate improvements.
- **Real-world failures vs academic optimizing.** Most real
  failures come from outside the clean algorithmic paradigm:
  population drift (distributions change over time), sample
  selectivity bias, mislabeled classes, arbitrary class
  definitions.
- **The flaw of comparative studies.** Breakthrough claims often
  suffer selection bias, developer-expertise skew, and no account
  of real-world uncertainty.
- **Parsimony.** Simple models are easier to interpret, maintain
  and deploy, so added classifier complexity frequently fails to
  justify its cost in practice.

**For the tab paper:** this is the §2 anchor for "the ground keeps
moving" and for benchmarking minima against maxima -- Hand's 85-90%
is the quantitative form of "a 7-bin Naive Bayes comes within [X]%
of LightGBM and TabPFN". His drift/selectivity points also argue
the fast-loop method: cheap learners make it affordable to re-check
conclusions when the population moves.
