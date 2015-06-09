#include "compression.h"

#include "gtest/gtest.h"

namespace grr {

TEST(CompressionTest, RoundTrip) {
  static const std::string kSentance =
      "The quick sly fox jumped over the lazy dogs.";
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kSentance)), kSentance);

  static const std::string kZeros(2048, '\0');
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kZeros)), kZeros);

  static const std::string kShort = "A";
  EXPECT_EQ(ZLib::Inflate(ZLib::Deflate(kShort)), kShort);
}
}  // namespace grr
