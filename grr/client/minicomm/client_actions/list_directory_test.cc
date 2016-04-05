#include "grr/client/minicomm/client_actions/list_directory.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace {
void WriteFile(const std::string& file_name) {
  std::ofstream file;
  file.open(file_name);
  file << "foo";
  file.close();
}
}

TEST(ListDirectory, SimpleTest) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::set<std::string> inserted = {
      temp_dir + "/fox.txt", temp_dir + "/host.conf", temp_dir + "/pam.conf",
      temp_dir + "/host"};

  for (auto& s : inserted) {
    WriteFile(s);
  }

  ListDirRequest spec;
  spec.mutable_pathspec()->set_path(temp_dir);
  spec.mutable_pathspec()->set_pathtype(PathSpec::OS);

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("ListDirRequest");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);
  actions::ListDirectory action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(10, 20000, true);

  std::set<std::string> check;
  for (const auto& m : r) {
    StatEntry u;
    ASSERT_TRUE(u.ParseFromString(m.args()));
    check.insert(u.mutable_pathspec()->path());
  }

  ASSERT_EQ(check.erase(temp_dir), 1);
  ASSERT_EQ(check, inserted);
}
}  // namespace grr
