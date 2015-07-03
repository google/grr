#include "grr/client/minicomm/util.h"

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

struct TestArrays {
  char A[10];
  char B[10];
  char C[1];
  char Z[1];
};

TEST(UtilTest, ArrayToString) {
  TestArrays test_arrays;

  // A properly terminated string of As.
  memset(test_arrays.A, 'A', sizeof(test_arrays.A));
  test_arrays.A[5] = '\0';

  // A string of Bs with the terminator cut off.
  memset(test_arrays.B, 'B', sizeof(test_arrays.B));

  test_arrays.C[0] = 'C';
  // Try to avoid UB if the template doesn't work.
  test_arrays.Z[0] = '\0';

  std::string A = ArrayToString(test_arrays.A);
  std::string B = ArrayToString(test_arrays.B);
  EXPECT_EQ("AAAAA", A);
  EXPECT_EQ("BBBBBBBBBB", B);

  // Make sure we didn't change anything else.
  EXPECT_EQ('C', test_arrays.C[0]);
}

}  // namespace grr
