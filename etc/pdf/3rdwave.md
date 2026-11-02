# Garcez & Lamb, Neurosymbolic AI: The 3rd Wave

pdf: garcez23neurosymbolic.pdf (arXiv 2012.05876; AI Review 2023).
See also [llms4science.md](llms4science.md) for the LLM-era poles.

**Their framing:** relate recent and early neurosymbolic results to
identify the key ingredients of the next wave of AI systems; focus
on research that integrates, in a principled way, neural
network-based learning with symbolic knowledge representation and
logical reasoning.

**Their central question:** how to compute and learn with symbols,
inside or outside of a neural network -- and how efficiently,
in a precise or approximate reasoning setting?

**For the tab paper:** tab's loop answers that question from the
outside-and-cheap corner: the symbols never enter the network.
A small symbolic artifact (lua code, golden tests, speed gates,
benchmarked minima) sits outside a neural generator (the LLM) and
referees it; integration is a verification loop, not a shared
representation. Precise, not approximate: any suggested change
reproduces byte-identical output or dies. In Kautz's taxonomy this
is Symbolic[Neuro] -- a symbolic harness invoking and checking a
neural assistant.
