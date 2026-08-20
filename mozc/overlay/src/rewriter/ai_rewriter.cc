#include "rewriter/ai_rewriter.h"

#include <algorithm>
#include <cstddef>
#include <string>
#include <utility>
#include <vector>

#include "converter/attribute.h"
#include "converter/candidate.h"
#include "converter/segments.h"
#include "rewriter/ai_ranker_client.h"

namespace mozc {

AiRewriter::AiRewriter(std::wstring pipe_name)
    : pipe_name_(std::move(pipe_name)) {}

int AiRewriter::capability(const ConversionRequest& request) const {
  // Keep AI out of prediction/suggestion paths: conversion is the path whose
  // candidates are committed and for which a context rerank is useful.
  (void)request;
  return RewriterInterface::CONVERSION;
}

bool AiRewriter::Rewrite(const ConversionRequest& request,
                         Segments* segments) const {
  if (segments == nullptr || segments->conversion_segments_size() == 0) {
    return false;
  }
  converter::Segment* segment = segments->mutable_conversion_segment(0);
  if (segment == nullptr || segment->candidates_size() < 2) return false;

  const size_t limit = std::min<size_t>(20, segment->candidates_size());
  std::vector<ai_ranker::CandidateInput> input;
  input.reserve(limit);
  for (size_t i = 0; i < limit; ++i) {
    const converter::Candidate& candidate = segment->candidate(i);
    input.push_back({"c" + std::to_string(i), candidate.value,
                     static_cast<int>(i + 1)});
  }

  ai_ranker::Client client(pipe_name_);
  std::vector<ai_ranker::RankedCandidate> ranked;
  // Some TSF hosts (notably Chromium/Electron editors) do not expose text
  // before the caret through ITfRange.  Mozc still retains recently committed
  // segments in the conversion session, so use that privacy-local history as
  // the context fallback instead of asking the model to rank context-free.
  std::string preceding_text(request.context().preceding_text());
  if (preceding_text.empty()) {
    preceding_text = segments->history_value();
  }
  const bool rank_ok = client.Rank(
      preceding_text,
      std::string(segment->key().data(), segment->key().size()), input,
      ai_ranker::kDefaultTimeoutMs, &ranked);
  if (!rank_ok ||
      ranked.size() != limit) {
    // The client does not modify |ranked| on failure; most importantly, this
    // function has not touched the Segment yet, so Mozc's order is preserved.
    return false;
  }

  // Validate the complete ID permutation before moving any candidate.  The
  // client performs the wire-schema checks too, but this second check binds
  // the response to this exact Segment and avoids partial mutation.
  std::vector<size_t> desired;
  desired.reserve(limit);
  std::vector<bool> seen(limit, false);
  for (size_t rank = 0; rank < ranked.size(); ++rank) {
    const std::string& id = ranked[rank].id;
    if (id.size() < 2 || id[0] != 'c') return false;
    size_t index = 0;
    for (size_t pos = 1; pos < id.size(); ++pos) {
      const char c = id[pos];
      if (c < '0' || c > '9') return false;
      index = index * 10 + static_cast<size_t>(c - '0');
      if (index >= limit) return false;
    }
    if (seen[index] || ranked[rank].rank != static_cast<int>(rank + 1)) {
      return false;
    }
    seen[index] = true;
    desired.push_back(index);
  }
  for (bool value : seen) {
    if (!value) return false;
  }

  // Every possible failure was checked above.  Keep a small permutation of
  // original local IDs so the actual Segment mutation has no fallible path.
  std::vector<size_t> current_ids(limit);
  for (size_t i = 0; i < limit; ++i) current_ids[i] = i;
  std::vector<std::pair<int, int>> moves;
  moves.reserve(limit);
  for (size_t target = 0; target < limit; ++target) {
    const auto current_it =
        std::find(current_ids.begin() + target, current_ids.end(),
                  desired[target]);
    if (current_it == current_ids.end()) return false;
    const size_t current = static_cast<size_t>(
        std::distance(current_ids.begin(), current_it));
    if (current != target) {
      moves.emplace_back(static_cast<int>(current), static_cast<int>(target));
      const size_t moved = current_ids[current];
      current_ids.erase(current_ids.begin() + current);
      current_ids.insert(current_ids.begin() + target, moved);
    }
  }
  for (const auto [current, target] : moves) {
    segment->move_candidate(current, target);
  }
  segment->mutable_candidate(0)->attributes |= converter::Attribute::RERANKED;
  return true;
}

}  // namespace mozc
