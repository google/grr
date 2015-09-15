#include "grr/client/minicomm/client_actions/find.h"

#include <sys/stat.h>

#include <fstream>

#include "gtest/gtest.h"
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

// This is the regex that the server sends to match the glob "*.conf".
const char kConfRegex[] = "(?i)^.*\\.conf\\Z(?ms)$";

}  // namespace

TEST(Find, RegexMatching) {
  const std::string temp_dir = testing::MakeTempDir();
  WriteFile(temp_dir + "/fox.txt");
  WriteFile(temp_dir + "/host.conf");
  WriteFile(temp_dir + "/pam.conf");
  WriteFile(temp_dir + "/hosts");

  FindSpec spec;
  spec.mutable_pathspec()->set_path(temp_dir);
  spec.mutable_pathspec()->set_pathtype(PathSpec::OS);
  spec.set_path_regex(kConfRegex);

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("FindSpec");
  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  actions::Find action;
  action.ProcessRequest(&context);

  const auto results = queue.GetMessages(5, 20000, false);
  EXPECT_EQ(3, results.size());

  std::set<std::string> found;
  for (const auto& result : results) {
    if (result.type() == GrrMessage::MESSAGE) {
      FindSpec res_spec;
      ASSERT_TRUE(res_spec.ParseFromString(result.args()));
      found.insert(res_spec.hit().pathspec().path());
    }
  }
  EXPECT_EQ(found.count(temp_dir + "/host.conf"), 1);
  EXPECT_EQ(found.count(temp_dir + "/pam.conf"), 1);
}

TEST(Find, RegexDeepMatching) {
  const std::string temp_dir = testing::MakeTempDir();
  std::string sub_dir = temp_dir;
  for (int i = 0; i < 10; i++) {
    WriteFile(sub_dir + "/host.conf");
    sub_dir += "/sub_dir";
    ASSERT_EQ(mkdir(sub_dir.c_str(), S_IRWXU), 0);
  }

  FindSpec spec;
  spec.mutable_pathspec()->set_path(temp_dir);
  spec.mutable_pathspec()->set_pathtype(PathSpec::OS);
  spec.set_path_regex(kConfRegex);

  spec.set_max_depth(5);

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("FindSpec");

  MessageQueue queue(20, 20000);
  ActionContext context(message, &queue, nullptr);

  actions::Find action;
  action.ProcessRequest(&context);

  const auto results = queue.GetMessages(20, 20000, false);

  // Expect 4 hits, from depths 1-5, plus the terminating iterator.
  EXPECT_EQ(5, results.size());
}

}  // namespace grr
