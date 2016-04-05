#include "grr/client/minicomm/test_util.h"

#include <memory>

#include "grr/client/minicomm/base.h"

namespace grr {
namespace testing {
namespace {
std::string* MakeBaseTempDir() {
  const char t[] = "/tmp/GrrTest.XXXXXX";

  std::unique_ptr<char[]> writeable(new char[sizeof(t)]);
  std::copy(t, t + sizeof(t), writeable.get());
  const char* result = mkdtemp(writeable.get());
  GOOGLE_CHECK(result != nullptr) << "Unable to make temp directory, errno:"
                                  << errno;
  return new std::string(result);
}
const std::string& BaseTempDir() {
  static const std::string* temp_dir = MakeBaseTempDir();
  return *temp_dir;
}
}  // namespace

std::string MakeTempDir() {
  const ::testing::TestInfo* const test_info =
      ::testing::UnitTest::GetInstance()->current_test_info();

  const std::string r(BaseTempDir() + "/" + test_info->test_case_name() + "." +
                      test_info->name());
  GOOGLE_CHECK(mkdir(r.c_str(), S_IRWXU) == 0);
  GOOGLE_LOG(INFO) << "Made temp directory: " << r;
  return r;
}
}  // namespace testing
}  // namespace grr
