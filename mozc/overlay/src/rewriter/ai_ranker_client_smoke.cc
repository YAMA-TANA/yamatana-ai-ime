#include <iostream>
#include <vector>

#include "rewriter/ai_ranker_client.h"

int main() {
  mozc::ai_ranker::Client client(L"\\\\.\\pipe\\ai_ime_ranker");
  const std::vector<mozc::ai_ranker::CandidateInput> candidates = {
      {"c0", "花", 1},
      {"c1", "鼻", 2},
  };
  std::vector<mozc::ai_ranker::RankedCandidate> ranked;
  if (!client.Rank("今日は", "はな", candidates, 500, &ranked)) {
    std::cerr << "AI_RANKER_CLIENT_SMOKE_FAIL\n";
    return 1;
  }
  std::cout << "AI_RANKER_CLIENT_SMOKE_PASS count=" << ranked.size() << "\n";
  return ranked.size() == candidates.size() ? 0 : 2;
}
