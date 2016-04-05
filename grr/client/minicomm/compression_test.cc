#include "grr/client/minicomm/compression.h"

#include <stdlib.h>

#include "gtest/gtest.h"

namespace grr {

TEST(CompressionTest, RoundTrip) {
  static const std::string kSentence =
      "The quick sly fox jumped over the lazy dogs.";
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kSentence)), kSentence);

  static const std::string kZeros(2048, '\0');
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kZeros)), kZeros);

  static const std::string kShort = "A";
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kShort)), kShort);
}

TEST(CompressionTest, ZDeflate) {
  static const char kSentence[] =
      "The quick sly fox jumped over the lazy dogs.";
  {
    ZDeflate sentence_deflate;
    // kSentence is an array with 44 printable symbols.
    sentence_deflate.Update(kSentence, 44);
    EXPECT_EQ(kSentence,
              ZLib::Inflate(sentence_deflate.Final()));
  }
  {
    ZDeflate sentence_deflate;
    // As an array, kSentence has a length of 45, because of the terminator, and
    // this is a hard limit on how much we read.
    sentence_deflate.Update(kSentence, 100);
    EXPECT_EQ(std::string(kSentence, 45),
              ZLib::Inflate(sentence_deflate.Final()));
  }
  {
    // Multiple input blocks.
    ZDeflate sentence_deflate;
    for (int i = 0; i < 10; i++) {
      sentence_deflate.Update(kSentence, 100);
    }
    const std::string sentences = ZLib::Inflate(sentence_deflate.Final());
    EXPECT_EQ(450, sentences.size());
  }
  {
    // Multiple output blocks. Force the output size to be larger than 64k
    // by compressing random numbers.
    srand(42);

    constexpr int kSize = 96 * 1024;
    char randoms[kSize];

    // Trust that sizeof(int) divides kSize.
    for (int i = 0; i < kSize / sizeof(int); i++) {
      *(reinterpret_cast<int *>(randoms) + i) = rand();
    }
    ZDeflate rand_deflate;
    rand_deflate.Update(randoms, kSize);
    const std::string compressed_result = rand_deflate.Final();
    EXPECT_GT(compressed_result.size(), 64 * 1024);
    const std::string result = ZLib::Inflate(compressed_result);
    EXPECT_EQ(result, std::string(randoms, kSize));
  }
}
}  // namespace grr
