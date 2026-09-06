#include "rewriter/ai_rewriter.h"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
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

namespace {

using Clock = std::chrono::steady_clock;

int RemainingBudgetMs(const Clock::time_point& deadline) {
  const auto now = Clock::now();
  if (now >= deadline) return 0;
  return static_cast<int>(
      std::chrono::duration_cast<std::chrono::milliseconds>(deadline - now)
          .count());
}

bool IsRerankableSegment(const converter::Segment& segment) {
  return segment.segment_type() == converter::Segment::FREE ||
         segment.segment_type() == converter::Segment::FIXED_BOUNDARY;
}

bool ApplyPermutation(converter::Segment* segment,
                      const std::vector<ai_ranker::RankedCandidate>& ranked,
                      size_t limit) {
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
      moves.emplace_back(static_cast<int>(current),
                         static_cast<int>(target));
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

}  // namespace

int AiRewriter::capability(const ConversionRequest& request) const {
  // Keep AI out of prediction/suggestion paths: conversion is the path whose
  // candidates are committed and for which a context rerank is useful.
  // RealtimeDecoder invokes the converter with CONVERSION request type while
  // the user is still typing.  It marks that internal request so expensive
  // rewriters can stay off the latency-critical path.
  if (request.options().skip_slow_rewriters ||
      request.options().used_in_predictor_realtime_conversion) {
    return RewriterInterface::NOT_AVAILABLE;
  }
  return RewriterInterface::CONVERSION;
}

std::optional<RewriterInterface::ResizeSegmentsRequest>
AiRewriter::CheckResizeSegmentsRequest(const ConversionRequest& request,
                                       const Segments& segments) const {
  if (request.options().skip_slow_rewriters ||
      request.options().used_in_predictor_realtime_conversion ||
      segments.resized()) {
    return std::nullopt;
  }
  const size_t count = segments.conversion_segments_size();
  if (count < 2 || count > 4) return std::nullopt;

  // A compound word may be split so that the intended surface form does not
  // exist in any individual segment (e.g. 主戦 + 率 instead of 主旋律).
  // When local context and the AI server are available, ask Mozc to generate
  // its normal candidates once more with a single short boundary.  AiRewriter
  // can then rank the real dictionary candidate without generating text.
  if (request.context().preceding_text().empty() &&
      segments.history_value().empty()) {
    return std::nullopt;
  }
  size_t total_key_chars = 0;
  for (const converter::Segment& segment : segments.conversion_segments()) {
    if (segment.segment_type() != converter::Segment::FREE) {
      return std::nullopt;
    }
    total_key_chars += segment.key_len();
  }
  constexpr size_t kMaxCompoundChars = 12;
  if (total_key_chars < 2 || total_key_chars > kMaxCompoundChars) {
    return std::nullopt;
  }
  ai_ranker::Client client(pipe_name_);
  if (!client.IsAvailable(25)) return std::nullopt;

  ResizeSegmentsRequest resize_request = {
      .segment_index = 0,
      .segment_sizes = {static_cast<uint8_t>(total_key_chars), 0, 0, 0, 0, 0,
                        0, 0},
  };
  return resize_request;
}

bool AiRewriter::Rewrite(const ConversionRequest& request,
                         Segments* segments) const {
  // Keep the direct-call path safe too.  MergerRewriter normally checks
  // capability(), but tests and other callers can invoke Rewrite directly.
  if (request.options().skip_slow_rewriters ||
      request.options().used_in_predictor_realtime_conversion) {
    return false;
  }
  if (segments == nullptr || segments->conversion_segments_size() == 0) {
    return false;
  }

  // Some TSF hosts (notably Chromium/Electron editors) do not expose text
  // before the caret through ITfRange.  Mozc still retains recently committed
  // segments in the conversion session, so use that privacy-local history as
  // the context fallback instead of asking the model to rank context-free.
  std::string preceding_text(request.context().preceding_text());
  if (preceding_text.empty()) {
    preceding_text = segments->history_value();
  }
  // With no preceding text there is no context to disambiguate homophones.
  // Preserve Mozc's well-tuned dictionary order instead of asking the model
  // to make a context-free guess.
  if (preceding_text.empty()) {
    return false;
  }

  const std::string trailing_text(request.context().following_text());

  // Pre-count the segments we may rerank so the budget is shared fairly.
  size_t rerankable_segments = 0;
  for (size_t i = 0; i < segments->conversion_segments_size(); ++i) {
    const converter::Segment& seg = segments->conversion_segment(i);
    if (IsRerankableSegment(seg) && seg.candidates_size() >= 2) {
      ++rerankable_segments;
    }
  }
  if (rerankable_segments == 0) {
    return false;
  }

  const Clock::time_point deadline =
      Clock::now() + std::chrono::milliseconds(ai_ranker::kDefaultTimeoutMs);
  ai_ranker::Client client(pipe_name_);
  std::string accumulated = preceding_text;
  bool any_reordered = false;

  for (size_t index = 0; index < segments->conversion_segments_size();
       ++index) {
    converter::Segment* segment = segments->mutable_conversion_segment(index);
    if (segment == nullptr || !IsRerankableSegment(*segment)) {
      continue;
    }
    if (segment->candidates_size() < 2) {
      accumulated.append(std::string(segment->key().data(),
                                     segment->key().size()));
      continue;
    }

    // The useful homophone candidates are concentrated near the top of
    // Mozc's list.  Eight candidates cover more than the visible first page
    // while keeping explicit Space-key inference responsive on CPU.
    const size_t limit =
        std::min<size_t>(8, segment->candidates_size());
    std::vector<ai_ranker::CandidateInput> input;
    input.reserve(limit);
    for (size_t i = 0; i < limit; ++i) {
      const converter::Candidate& candidate = segment->candidate(i);
      input.push_back({"c" + std::to_string(i), candidate.value,
                       static_cast<int>(i + 1)});
    }

    // Compose the suffix from later free segments' top candidate values
    // and the text following the conversion point.  This lets the ranker
    // disambiguate phrases such as 「庭には美しい●が咲く」.
    std::string following_text = trailing_text;
    for (size_t later = index + 1;
         later < segments->conversion_segments_size(); ++later) {
      const converter::Segment& later_seg = segments->conversion_segment(later);
      if (later_seg.candidates_size() == 0) {
        continue;
      }
      following_text.append(
          std::string(later_seg.candidate(0).value.data(),
                      later_seg.candidate(0).value.size()));
    }

    const int remaining_ms = RemainingBudgetMs(deadline);
    if (remaining_ms <= 0) break;

    std::vector<ai_ranker::RankedCandidate> ranked;
    const bool rank_ok = client.Rank(
        accumulated, following_text,
        std::string(segment->key().data(), segment->key().size()), input,
        remaining_ms, &ranked);
    if (!rank_ok || ranked.size() != limit) {
      // Preserve Mozc's order for this segment but keep going so later
      // segments still receive context built from this segment's top value.
      accumulated.append(std::string(segment->candidate(0).value.data(),
                                     segment->candidate(0).value.size()));
      continue;
    }

    if (ApplyPermutation(segment, ranked, limit)) {
      any_reordered = true;
    }
    accumulated.append(std::string(segment->candidate(0).value.data(),
                                   segment->candidate(0).value.size()));
  }

  return any_reordered;
}

}  // namespace mozc
