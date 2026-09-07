#include "rewriter/ai_rewriter.h"

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "base/util.h"
#include "converter/attribute.h"
#include "converter/candidate.h"
#include "converter/segments.h"
#include "dictionary/dictionary_interface.h"
#include "rewriter/ai_ranker_client.h"

namespace mozc {

AiRewriter::AiRewriter(std::wstring pipe_name)
    : AiRewriter(nullptr, std::move(pipe_name)) {}

AiRewriter::AiRewriter(const dictionary::DictionaryInterface* dictionary,
                       std::wstring pipe_name)
    : dictionary_(dictionary), pipe_name_(std::move(pipe_name)) {}

namespace {

using Clock = std::chrono::steady_clock;

constexpr size_t kBoundaryDictionaryLimit = 6;
constexpr size_t kBoundaryRepairLimit = 12;
constexpr int kBoundaryProbeTimeoutMs = 700;
constexpr double kBoundaryRepairMargin = 0.60;

struct SurfaceOption {
  std::string value;
  int64_t cost = 0;
};

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

bool IsGrammarLikeKey(absl::string_view key) {
  return key == "こと" || key == "もの" || key == "ため" ||
         key == "よう" || key == "ので" || key == "のに" ||
         key == "から" || key == "まで" || key == "だけ" ||
         key == "ほど" || key == "する" || key == "した" ||
         key == "して" || key == "です" || key == "ます" ||
         key == "いる" || key == "ある" || key == "なる" ||
         key == "ない" || key == "たい" || key == "れる" ||
         key == "られる" || key == "せる" || key == "させる";
}

void AddSurfaceOption(std::vector<SurfaceOption>* options, std::string value,
                      int64_t cost) {
  if (options == nullptr || value.empty()) return;
  auto existing = std::find_if(options->begin(), options->end(),
                               [&](const SurfaceOption& option) {
                                 return option.value == value;
                               });
  if (existing == options->end()) {
    options->push_back({std::move(value), cost});
  } else if (cost < existing->cost) {
    existing->cost = cost;
  }
}

std::vector<SurfaceOption> LookupExactSurfaces(
    const dictionary::DictionaryInterface* dictionary, absl::string_view key,
    size_t limit = kBoundaryDictionaryLimit) {
  std::vector<SurfaceOption> options;
  if (dictionary == nullptr || key.empty()) return options;

  dictionary::InlineCallback callback;
  callback.OnToken(
      [&](absl::string_view, absl::string_view,
          const dictionary::Token& token) {
        AddSurfaceOption(&options, token.value, token.cost);
        return dictionary::DictionaryInterface::Callback::TRAVERSE_CONTINUE;
      });
  dictionary->LookupExact(key, &callback);

  std::sort(options.begin(), options.end(),
            [](const SurfaceOption& lhs, const SurfaceOption& rhs) {
              if (lhs.cost != rhs.cost) return lhs.cost < rhs.cost;
              return lhs.value < rhs.value;
            });
  if (options.size() > limit) options.resize(limit);
  return options;
}

bool ContainsSurface(const std::vector<SurfaceOption>& options,
                     absl::string_view value) {
  return std::any_of(options.begin(), options.end(),
                     [&](const SurfaceOption& option) {
                       return option.value == value;
                     });
}

bool SegmentContainsSurface(const converter::Segment& segment,
                            absl::string_view value) {
  for (size_t i = 0; i < segment.candidates_size(); ++i) {
    if (segment.candidate(i).value == value) return true;
  }
  return false;
}

std::vector<SurfaceOption> BuildSplitSurfaces(
    const dictionary::DictionaryInterface* dictionary,
    absl::string_view left_key, absl::string_view right_key) {
  const std::vector<SurfaceOption> left =
      LookupExactSurfaces(dictionary, left_key);
  const std::vector<SurfaceOption> right =
      LookupExactSurfaces(dictionary, right_key);
  std::vector<SurfaceOption> combined;
  if (left.empty() || right.empty()) return combined;

  for (const SurfaceOption& lhs : left) {
    for (const SurfaceOption& rhs : right) {
      AddSurfaceOption(&combined, lhs.value + rhs.value, lhs.cost + rhs.cost);
    }
  }
  std::sort(combined.begin(), combined.end(),
            [](const SurfaceOption& lhs, const SurfaceOption& rhs) {
              if (lhs.cost != rhs.cost) return lhs.cost < rhs.cost;
              return lhs.value < rhs.value;
            });
  if (combined.size() > kBoundaryRepairLimit) {
    combined.resize(kBoundaryRepairLimit);
  }
  return combined;
}

std::string SegmentTopSurface(const converter::Segment& segment) {
  if (segment.candidates_size() > 0) {
    return std::string(segment.candidate(0).value);
  }
  return std::string(segment.key());
}

std::string CurrentSurface(const Segments& segments) {
  std::string surface;
  for (const converter::Segment& segment : segments.conversion_segments()) {
    surface.append(SegmentTopSurface(segment));
  }
  return surface;
}

std::string FullReading(const Segments& segments) {
  std::string reading;
  for (const converter::Segment& segment : segments.conversion_segments()) {
    reading.append(segment.key().data(), segment.key().size());
  }
  return reading;
}

std::vector<std::string> RepairValues(
    const std::vector<SurfaceOption>& options, absl::string_view baseline,
    const std::vector<SurfaceOption>* blocked = nullptr) {
  std::vector<std::string> values;
  for (const SurfaceOption& option : options) {
    if (option.value == baseline) continue;
    if (blocked != nullptr && ContainsSurface(*blocked, option.value)) continue;
    if (std::find(values.begin(), values.end(), option.value) != values.end()) {
      continue;
    }
    values.push_back(option.value);
    if (values.size() >= kBoundaryRepairLimit) break;
  }
  return values;
}

bool BoundaryRepairWins(const ai_ranker::Client& client,
                        const ConversionRequest& request,
                        const Segments& segments, const std::string& reading,
                        const std::string& baseline,
                        const std::vector<std::string>& repairs) {
  if (baseline.empty() || repairs.empty()) return false;

  std::vector<ai_ranker::CandidateInput> candidates;
  candidates.reserve(repairs.size() + 1);
  candidates.push_back({"baseline", baseline, 1});
  for (size_t i = 0; i < repairs.size(); ++i) {
    candidates.push_back({"repair" + std::to_string(i), repairs[i],
                          static_cast<int>(i + 2)});
  }

  std::string preceding_text(request.context().preceding_text());
  if (preceding_text.empty()) preceding_text = segments.history_value();
  const std::string following_text(request.context().following_text());

  std::vector<ai_ranker::RankedCandidate> ranked;
  if (!client.Rank(preceding_text, following_text, reading, candidates,
                   kBoundaryProbeTimeoutMs, &ranked) ||
      ranked.size() != candidates.size() || ranked.empty()) {
    return false;
  }

  const auto baseline_it =
      std::find_if(ranked.begin(), ranked.end(), [](const auto& item) {
        return item.id == "baseline";
      });
  if (baseline_it == ranked.end() ||
      ranked.front().id.rfind("repair", 0) != 0) {
    return false;
  }
  return ranked.front().score - baseline_it->score >= kBoundaryRepairMargin;
}

bool ApplyPermutation(converter::Segment* segment,
                      const std::vector<ai_ranker::RankedCandidate>& ranked,
                      size_t limit) {
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
  if (count == 0 || count > 4 || dictionary_ == nullptr) {
    return std::nullopt;
  }

  ai_ranker::Client client(pipe_name_);
  if (!client.IsAvailable(25)) return std::nullopt;

  constexpr size_t kMinCompoundChars = 4;
  constexpr size_t kMaxCompoundChars = 12;

  if (count == 1) {
    const converter::Segment& segment = segments.conversion_segment(0);
    if (!IsRerankableSegment(segment) || segment.candidates_size() == 0 ||
        segment.candidates_size() > 4) {
      return std::nullopt;
    }
    const std::string key(segment.key());
    const size_t key_chars = Util::CharsLen(key);
    if (key_chars < kMinCompoundChars || key_chars > kMaxCompoundChars) {
      return std::nullopt;
    }

    size_t split_chars = 0;
    size_t valid_splits = 0;
    for (size_t split = 2; split + 2 <= key_chars; ++split) {
      const absl::string_view prefix = Util::Utf8SubString(key, 0, split);
      const absl::string_view suffix =
          Util::Utf8SubString(key, split, key_chars - split);
      if (dictionary_->HasKey(prefix) && dictionary_->HasKey(suffix)) {
        split_chars = split;
        ++valid_splits;
      }
    }
    if (valid_splits != 1) return std::nullopt;

    const absl::string_view left_key = Util::Utf8SubString(key, 0, split_chars);
    const absl::string_view right_key =
        Util::Utf8SubString(key, split_chars, key_chars - split_chars);
    const std::vector<SurfaceOption> split_surfaces =
        BuildSplitSurfaces(dictionary_, left_key, right_key);
    std::vector<std::string> repairs;
    const std::string baseline = SegmentTopSurface(segment);
    for (const SurfaceOption& option : split_surfaces) {
      if (option.value == baseline || SegmentContainsSurface(segment, option.value)) {
        continue;
      }
      repairs.push_back(option.value);
      if (repairs.size() >= kBoundaryRepairLimit) break;
    }
    if (!BoundaryRepairWins(client, request, segments, key, baseline, repairs)) {
      return std::nullopt;
    }

    ResizeSegmentsRequest resize_request = {
        .segment_index = 0,
        .segment_sizes = {
            static_cast<uint8_t>(split_chars),
            static_cast<uint8_t>(key_chars - split_chars), 0, 0, 0, 0, 0, 0},
    };
    return resize_request;
  }

  if (count != 2) return std::nullopt;

  size_t total_key_chars = 0;
  for (const converter::Segment& segment : segments.conversion_segments()) {
    if (segment.segment_type() != converter::Segment::FREE ||
        segment.candidates_size() == 0) {
      return std::nullopt;
    }
    total_key_chars += segment.key_len();
  }
  if (total_key_chars < 2 || total_key_chars > kMaxCompoundChars) {
    return std::nullopt;
  }

  const converter::Segment& first = segments.conversion_segment(0);
  const converter::Segment& second = segments.conversion_segment(1);
  const std::string reading = FullReading(segments);
  const std::string baseline = CurrentSurface(segments);
  ResizeSegmentsRequest resize_request = {.segment_index = 0};

  if (second.key_len() <= 2) {
    if (total_key_chars < kMinCompoundChars || IsGrammarLikeKey(first.key()) ||
        IsGrammarLikeKey(second.key())) {
      return std::nullopt;
    }
    const std::vector<SurfaceOption> whole_surfaces =
        LookupExactSurfaces(dictionary_, reading, kBoundaryRepairLimit);
    const std::vector<std::string> repairs =
        RepairValues(whole_surfaces, baseline);
    if (!BoundaryRepairWins(client, request, segments, reading, baseline,
                            repairs)) {
      return std::nullopt;
    }
    resize_request.segment_sizes[0] =
        static_cast<uint8_t>(total_key_chars);
    return resize_request;
  }

  // Lock an existing two-word boundary only when it exposes a whole-surface
  // reading that the unsegmented dictionary path does not offer and the AI
  // clearly prefers that split-only path.  This is the transactional version
  // of the old 飛行 + 少年 protection: no confident repair, no boundary change.
  const std::vector<SurfaceOption> whole_surfaces =
      LookupExactSurfaces(dictionary_, reading, kBoundaryRepairLimit);
  if (whole_surfaces.empty()) return std::nullopt;
  const std::vector<SurfaceOption> split_surfaces =
      BuildSplitSurfaces(dictionary_, first.key(), second.key());
  const std::vector<std::string> repairs =
      RepairValues(split_surfaces, baseline, &whole_surfaces);
  if (!BoundaryRepairWins(client, request, segments, reading, baseline,
                          repairs)) {
    return std::nullopt;
  }
  resize_request.segment_sizes[0] = static_cast<uint8_t>(first.key_len());
  resize_request.segment_sizes[1] = static_cast<uint8_t>(second.key_len());
  return resize_request;
}

bool AiRewriter::Rewrite(const ConversionRequest& request,
                         Segments* segments) const {
  if (request.options().skip_slow_rewriters ||
      request.options().used_in_predictor_realtime_conversion) {
    return false;
  }
  if (segments == nullptr || segments->conversion_segments_size() == 0) {
    return false;
  }

  std::string preceding_text(request.context().preceding_text());
  if (preceding_text.empty()) {
    preceding_text = segments->history_value();
  }
  const std::string trailing_text(request.context().following_text());
  const bool has_in_composition_context =
      !trailing_text.empty() || segments->conversion_segments_size() > 1;
  // Preserve the conservative single-word/no-context behavior, but do not
  // disable AI for an entire sentence just because nothing was committed
  // before the current composition.  Later conversion segments provide real
  // following context to the first segment and accumulated context thereafter.
  if (preceding_text.empty() && !segments->resized() &&
      !has_in_composition_context) {
    return false;
  }

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

    const size_t limit = segment->candidates_size();
    std::vector<ai_ranker::CandidateInput> input;
    input.reserve(limit);
    for (size_t i = 0; i < limit; ++i) {
      const converter::Candidate& candidate = segment->candidate(i);
      input.push_back({"c" + std::to_string(i), candidate.value,
                       static_cast<int>(i + 1)});
    }

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