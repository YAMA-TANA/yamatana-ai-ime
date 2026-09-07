# AI rerank ordering regression

This branch fixes a production regression where the AI ranker could successfully reorder candidates, but later Mozc rewriters (especially user history) could change the order again before the candidate list was shown or committed.

The fix separates early AI boundary planning from final candidate reranking, runs final AI reranking after Mozc's normal rewrite chain, allows current-composition following segments to provide context at sentence start, and marks `RERANKED` only when a non-Mozc-top candidate is actually promoted to rank 1.

Regression tests cover successful candidate promotion, sentence-start multi-segment context, and unchanged-order behavior.
