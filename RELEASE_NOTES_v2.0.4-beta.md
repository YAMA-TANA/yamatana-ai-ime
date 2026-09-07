# Yamatana AI IME v2.0.4-beta

v2.0.4-beta fixes a production candidate-ordering bug where a successful AI rerank could be overwritten by later Mozc rewriters before the candidate list was displayed or committed.

## Fixed

- **AI candidate ranking now becomes the final conversion order.**
  - Boundary planning remains early so useful Mozc segment boundaries can still be repaired or preserved.
  - Candidate reranking now runs after Mozc's normal rewrite chain, including user-history rewriters, so later Mozc logic cannot silently restore the old order.
- **Sentence-start multi-segment conversion can use AI context.**
  - A composition is no longer skipped merely because no text was committed before it.
  - Later segments in the current conversion are used as following context.
  - Isolated single-word conversion with no context still falls back conservatively to Mozc.
- **Rerank status now matches actual behavior.**
  - An unchanged AI permutation no longer reports a candidate-order update.
  - `RERANKED` is set only when a non-Mozc-top candidate is actually promoted to rank 1.
  - The AI badge therefore corresponds to a real top-candidate promotion instead of merely a successful inference call.
- Updated the modern UI patch step so packaged Mozc builds remain compatible with the corrected rerank implementation.

## Regression coverage

Windows/Mozc tests now verify that:

- when the ranker selects `c1`, it really becomes candidate 0 in the Mozc segment;
- sentence-start conversion can use a following segment as context;
- unchanged AI order remains unchanged and is not marked as reranked.

Both the normal Windows CI and the dedicated Bazel Mozc rewriter test passed before this fix was merged.

## Existing v2.0.3 behavior retained

- Local 70M ONNX reranker.
- Score-aware neural reranking with a soft logarithmic Mozc rank prior.
- Ambiguity protection for weak context.
- Compound boundary repair safeguards.
- DirectML provider verification with CPU fallback in automatic mode.
- Local-only inference and document-domain settings.
- Modern Windows candidate UI.

## Beta notice

This is an unsigned beta MSI. Windows may display a SmartScreen or publisher warning during installation.
