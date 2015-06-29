#include "grr/client/minicomm/test_util.h"

#include <memory>

#include "grr/client/minicomm/base.h"

namespace grr {
namespace testing {
std::string MakeTempDir() {
  const ::testing::TestInfo* const test_info =
      ::testing::UnitTest::GetInstance()->current_test_info();
  std::string t = "/tmp/GrrTest.";
  t.append(test_info->test_case_name());
  t.append(".");
  t.append(test_info->name());
  t.append(".XXXXXX");

  std::unique_ptr<char[]> writeable(new char[t.size()+1]);
  std::copy(t.begin(), t.end(), writeable.get());
  writeable[t.size()] = '\0';
  const char* result = mkdtemp(writeable.get());
  GOOGLE_CHECK(result != nullptr) << "Unable to make temp directory, errno:"
                                  << errno;
  const std::string r(result);
  GOOGLE_LOG(INFO) << "Created temporary directory: " << r;
  return std::string(r);
}
}  // namespace testing
}  // namespace grr
