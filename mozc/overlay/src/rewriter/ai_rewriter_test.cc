#include "rewriter/ai_rewriter.h"

#include "converter/candidate.h"
#include "converter/segments.h"
#include "request/conversion_request.h"
#include "rewriter/rewriter_interface.h"
#include "testing/gunit.h"

namespace mozc {

TEST(AiRewriterTest, CapabilityIsConversionOnly) {
  AiRewriter rewriter(L"missing-ai-ime-pipe");
  const ConversionRequest request;
  EXPECT_EQ(rewriter.capability(request), RewriterInterface::CONVERSION);
}

TEST(AiRewriterTest, RankerFailurePreservesMozcOrder) {
  Segments segments;
  Segment* segment = segments.add_segment();
  segment->set_key("hana");
  converter::Candidate* first = segment->add_candidate();
  first->key = "hana";
  first->value = "花";
  converter::Candidate* second = segment->add_candidate();
  second->key = "hana";
  second->value = "鼻";

  AiRewriter rewriter(L"missing-ai-ime-pipe");
  const ConversionRequest request;
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  ASSERT_EQ(segments.segment(0).candidates_size(), 2);
  EXPECT_EQ(segments.segment(0).candidate(0).value, "花");
  EXPECT_EQ(segments.segment(0).candidate(1).value, "鼻");
}

}  // namespace mozc
