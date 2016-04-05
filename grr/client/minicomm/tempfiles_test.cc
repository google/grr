#include "grr/client/minicomm/tempfiles.h"

#include <unistd.h>

#include <fstream>
#include <vector>

#include "gtest/gtest.h"
#include "grr/client/minicomm/client_test_base.h"
#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace {}

class TempFilesTest : public grr::ClientTestBase {};

TEST_F(TempFilesTest, CreateAndDelete) {
  std::vector<std::string> files;
  WriteValidConfigFile(false, true);
  ASSERT_TRUE(config_.ReadConfig());

  TemporaryFiles temp_files(config_);

  for (int i = 0; i < 50; ++i) {
    std::string path;
    std::string error;
    path = temp_files.CreateGRRTempFile("Testing", &error);
    ASSERT_GT(path.size(), 0);
    ASSERT_EQ(access(path.c_str(), R_OK), 0);
    files.emplace_back(path);
  }

  std::string error;
  std::string log;

  ASSERT_TRUE(temp_files.DeleteGRRTempFiles(config_.TemporaryDirectory(), &log,
                                            &error));
  ASSERT_GT(log.size(), 0);

  for (auto& file : files) {
    ASSERT_EQ(access(file.c_str(), R_OK), -1);
  }
}
}  // namespace grr
