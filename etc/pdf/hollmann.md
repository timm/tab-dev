# Hollmann et al., TabPFN

pdfs: hollmann23tabpfn.pdf (ICLR 2023);
hollmann25tabpfn2.pdf (Nature 2025, "Accurate predictions on small
data with a tabular foundation model").  The maxima arm in the tab
paper's benchmarks.

Their framing (Nature 2025, intro):

> Throughout the history of artificial intelligence, manually
> created algorithmic components have been replaced with
> better-performing end-to-end learned ones.  Hand-designed
> features in computer vision, such as SIFT and HOG, have been
> replaced by learned convolutions; grammar-based approaches in
> natural language processing have been replaced by learned
> transformers; and the design of customized opening and end-game
> libraries in game playing has been superseded by end-to-end
> learned strategies.  Here we extend this end-to-end learning to
> the ubiquitous domain of tabular data.
>
> The diversity of tabular data sets them apart from unprocessed
> modalities such as text and images.  While in language modelling
> for example the meaning of a word is consistent across documents,
> in tabular datasets the same value can mean fundamentally
> different things.  A drug discovery dataset, for example, might
> record chemical properties, whereas another dataset in materials
> science might document thermal and electric properties.  This
> specialization leads to a proliferation of smaller, independent
> datasets and associated models.  To illustrate, on the popular
> tabular benchmarking website openml.org, 76% of the datasets
> contain less than 10,000 rows at the time of writing.

**For the tab paper:** the perfect foil, twice over.

1. Their opening paragraph is the end-to-end creed stated plainly:
   the arc of AI bends toward replacing hand-made components with
   learned ones.  tab's thesis is the counter-move for science
   instruments: use the learned thing to *search*, but ship the
   hand-sized symbolic artifact (energy, verifiability, longevity).
2. Their own motivating statistic -- 76% of OpenML datasets under
   10k rows -- cuts both ways.  They read it as "small data needs a
   foundation model's prior".  It equally reads as "most tabular
   problems live exactly where very small learners are known to be
   competitive" (Hand 2006, Holte 1993, Grinsztajn 2022).  Same
   fact, opposite conclusions; the benchmarks decide, which is why
   TabPFN is tab's maxima arm.

## How the 80/20 split maps onto in-context learning

TabPFN/TabICL never fit anything to your data.  "TabPFN is trained
on synthetic data to take entire datasets as inputs and predict in
a forward pass": the 80% train split enters the transformer's
context as labeled examples, the 20% rides along as queries, one
forward pass emits all predictions.  No gradients, no weight
updates on your data -- all learning happened once, in pre-training
on millions of synthetic datasets; at use time the frozen net
"learns" your table via attention over the context, as in few-shot
LLM prompting.

Consequences for the tab paper:

1. **The cost structure inverts.**  tab.lua pays O(rows) once at
   training, then each guess is O(columns).  TabPFN pays nothing at
   "training" but every prediction attends over the whole 80%:
   inference cost scales with training-set size.  Their "5,140x
   speedup" is against 4 hours of boosted-tree tuning; against a
   learner whose total budget is milliseconds, it reads differently.
2. **Hard caps.**  v2 handles up to 10,000 samples and 500 features
   (classification <= 10 classes), so on bigger sets the 80% must
   be subsampled before it fits the context -- there the model
   genuinely does ignore most of the training data, by necessity.
3. **One-line analogy:** k-nearest-neighbor with a learned prior --
   memorize the training set, defer all learning to query time,
   except the "distance function" is layers of attention
   pre-trained on synthetic worlds.
