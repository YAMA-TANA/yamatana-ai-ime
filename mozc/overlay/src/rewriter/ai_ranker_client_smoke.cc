#include <iostream>
#include <vector>

#include "rewriter/ai_ranker_client.h"

int main() {
  mozc::ai_ranker::Client client(L"\\\\.\\pipe\\ai_ime_ranker");
  const std::vector<mozc::ai_ranker::CandidateInput> candidates = {
      {"c0", "主戦率", 1}, {"c1", "主戦律", 2},
      {"c2", "主線率", 3}, {"c3", "主旋律", 4},
      {"c4", "主選率", 5}, {"c5", "主戦立", 6},
      {"c6", "主線律", 7}, {"c7", "主選律", 8},
  };
  std::vector<mozc::ai_ranker::RankedCandidate> ranked;
  if (!client.Rank("この曲の", "は", "しゅせんりつ", candidates,
                   mozc::ai_ranker::kDefaultTimeoutMs, &ranked)) {
    std::cerr << "AI_RANKER_CLIENT_SMOKE_FAIL\n";
    return 1;
  }
  if (ranked.size() != candidates.size() || ranked.front().id != "c3") {
    std::cerr << "AI_RANKER_CLIENT_SMOKE_WRONG_TOP\n";
    return 2;
  }
  std::cout << "AI_RANKER_CLIENT_SMOKE_PASS top=主旋律 count="
            << ranked.size() << "\n";
  return 0;
}
