#include "rewriter/ai_rewriter.h"

#include <utility>

#ifdef _WIN32
#include <windows.h>
#endif

#include "converter/candidate.h"
#include "converter/segments.h"
#include "protocol/commands.pb.h"
#include "request/conversion_request.h"
#include "rewriter/rewriter_interface.h"
#include "testing/gunit.h"

namespace mozc {

TEST(AiRewriterTest, CapabilityIsConversionOnly) {
  AiRewriter rewriter(L"missing-ai-ime-pipe");
  const ConversionRequest request;
  EXPECT_EQ(rewriter.capability(request), RewriterInterface::CONVERSION);
}

TEST(AiRewriterTest, RealtimeConversionSkipsAiRanker) {
  ConversionRequest::Options options;
  options.request_type = ConversionRequest::CONVERSION;
  options.skip_slow_rewriters = true;
  const ConversionRequest request =
      ConversionRequestBuilder().SetOptions(std::move(options)).Build();

  AiRewriter rewriter(L"missing-ai-ime-pipe");
  EXPECT_EQ(rewriter.capability(request), RewriterInterface::NOT_AVAILABLE);

  Segments segments;
  Segment* segment = segments.add_segment();
  converter::Candidate* first = segment->add_candidate();
  first->value = "花";
  converter::Candidate* second = segment->add_candidate();
  second->value = "鼻";

  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  EXPECT_EQ(segments.segment(0).candidate(0).value, "花");
  EXPECT_EQ(segments.segment(0).candidate(1).value, "鼻");
}

TEST(AiRewriterTest, PredictorRealtimeMarkerSkipsAiRanker) {
  ConversionRequest::Options options;
  options.request_type = ConversionRequest::CONVERSION;
  options.used_in_predictor_realtime_conversion = true;
  const ConversionRequest request =
      ConversionRequestBuilder().SetOptions(std::move(options)).Build();

  AiRewriter rewriter(L"missing-ai-ime-pipe");
  EXPECT_EQ(rewriter.capability(request), RewriterInterface::NOT_AVAILABLE);

  Segments segments;
  Segment* segment = segments.add_segment();
  segment->add_candidate()->value = "花";
  segment->add_candidate()->value = "鼻";
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
}

#ifdef _WIN32
TEST(AiRewriterTest, AvailableRankerMergesShortCompoundForWholeWordCandidates) {
  const std::wstring pipe_name =
      L"\\\\.\\pipe\\yamatana_ai_rewriter_resize_test";
  HANDLE pipe = CreateNamedPipeW(pipe_name.c_str(), PIPE_ACCESS_DUPLEX,
                                 PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                 1, 4096, 4096, 0, nullptr);
  ASSERT_NE(pipe, INVALID_HANDLE_VALUE);

  Segments segments;
  Segment* first = segments.add_segment();
  first->set_key("しゅせん");
  first->add_candidate()->value = "主戦";
  Segment* second = segments.add_segment();
  second->set_key("りつ");
  second->add_candidate()->value = "率";

  commands::Context context;
  context.set_preceding_text("この曲の");
  const ConversionRequest request =
      ConversionRequestBuilder().SetContext(context).Build();
  AiRewriter rewriter(pipe_name);
  const auto resize = rewriter.CheckResizeSegmentsRequest(request, segments);
  CloseHandle(pipe);

  ASSERT_TRUE(resize.has_value());
  EXPECT_EQ(resize->segment_index, 0);
  EXPECT_EQ(resize->segment_sizes[0], 6);
  for (size_t i = 1; i < resize->segment_sizes.size(); ++i) {
    EXPECT_EQ(resize->segment_sizes[i], 0);
  }
}
#endif

TEST(AiRewriterTest, NoContextPreservesMozcOrder) {
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

TEST(AiRewriterTest, RankerFailureWithContextPreservesMozcOrder) {
  Segments segments;
  Segment* segment = segments.add_segment();
  segment->set_key("hana");
  converter::Candidate* first = segment->add_candidate();
  first->key = "hana";
  first->value = "花";
  converter::Candidate* second = segment->add_candidate();
  second->key = "hana";
  second->value = "鼻";

  commands::Context context;
  context.set_preceding_text("象の長い");
  const ConversionRequest request =
      ConversionRequestBuilder().SetContext(context).Build();
  AiRewriter rewriter(L"missing-ai-ime-pipe");
  EXPECT_FALSE(rewriter.Rewrite(request, &segments));
  ASSERT_EQ(segments.segment(0).candidates_size(), 2);
  EXPECT_EQ(segments.segment(0).candidate(0).value, "花");
  EXPECT_EQ(segments.segment(0).candidate(1).value, "鼻");
}

}  // namespace mozc
