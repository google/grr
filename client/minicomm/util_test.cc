#include "util.h"

#include "gtest/gtest.h"

namespace grr {

TEST(UtilTest, BytesToHex) {
  EXPECT_EQ("00", BytesToHex(std::string("\0", 1)));
  EXPECT_EQ("0000", BytesToHex(std::string("\0\0", 2)));
  EXPECT_EQ("3030", BytesToHex(std::string("00")));
  EXPECT_EQ("617364663b", BytesToHex(std::string("asdf;")));
  EXPECT_EQ("deadbeef", BytesToHex(std::string("\xDE\xAD\xBE\xEF")));
}

TEST(UtilTest, UrlDirname) {
  EXPECT_EQ("http://localhost:8001",
            UrlDirname("http://localhost:8001/control"));
  EXPECT_EQ("", UrlDirname("bad url"));
}
}  // namespace grr
