#ifndef GRR_CLIENT_MINICOMM_TEST_UTIL_H_
#define GRR_CLIENT_MINICOMM_TEST_UTIL_H_

#include "gtest/gtest.h"

namespace grr {
namespace testing {
// Make a temporary directory named for the test which is currently running.
std::string MakeTempDir();
}
}
#endif  // GRR_CLIENT_MINICOMM_TEST_UTIL_H_
