#ifndef MOZC_REWRITER_AI_RANKER_CLIENT_H_
#define MOZC_REWRITER_AI_RANKER_CLIENT_H_

#include <string>
#include <vector>

namespace mozc {
namespace ai_ranker {

// Default end-to-end budget for the optional ranker call.  A timeout keeps
// Mozc responsive and preserves its original candidate order.
constexpr int kDefaultTimeoutMs = 500;

// A request candidate is deliberately a copy of Mozc's existing value.  The
// ranker can only return one of these IDs; it cannot create a replacement.
struct CandidateInput {
  std::string id;
  std::string value;
  int original_rank = 0;
};

struct RankedCandidate {
  std::string id;
  double score = 0.0;
  int rank = 0;
};

class Client {
 public:
  explicit Client(std::wstring pipe_name);

  // Returns false on every transport, deadline, or schema error.  |ranked|
  // is not modified on failure, so callers can preserve Mozc's ordering.
  bool Rank(const std::string& preceding_text, const std::string& reading,
            const std::vector<CandidateInput>& candidates, int timeout_ms,
            std::vector<RankedCandidate>* ranked) const;

 private:
  std::wstring pipe_name_;
};

}  // namespace ai_ranker
}  // namespace mozc

#endif  // MOZC_REWRITER_AI_RANKER_CLIENT_H_
