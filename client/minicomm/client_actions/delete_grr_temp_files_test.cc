#include "grr/client/minicomm/client_actions/delete_grr_temp_files.h"

#include <unistd.h>

#include <fstream>
#include <vector>

#include "gtest/gtest.h"
#include "grr/client/minicomm/client_test_base.h"
#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/tempfiles.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace {}

class DeleteGRRTempFiles : public grr::ClientTestBase {};

TEST_F(DeleteGRRTempFiles, ActionTest) {
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

  PathSpec spec;
  spec.set_path(config_.TemporaryDirectory());
  spec.set_pathtype(PathSpec::OS);

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("PathSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, &config_);
  actions::DeleteGRRTempFiles action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(10, 20000, true);

  for (auto& file : files) {
    ASSERT_EQ(access(file.c_str(), R_OK), -1);
  }
}
}  // namespace grr
