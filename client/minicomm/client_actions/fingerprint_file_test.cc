#include "grr/client/minicomm/client_actions/fingerprint_file.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {

TEST(FingerprintFile, FingerprintNormal) {
  MessageQueue queue(5, 20000);
  actions::FingerprintFile action;
  const std::string temp_dir = testing::MakeTempDir();

  const std::string file_name = temp_dir + "/text";
  const char kSentance[] = "The quick brown fox jumped over the lazy dogs.\n";
  std::ofstream file;
  file.open(file_name);
  file << kSentance;
  file << '\0';
  file << kSentance;
  file.close();

  FingerprintRequest req;
  req.mutable_pathspec()->set_pathtype(PathSpec::OS);
  req.mutable_pathspec()->set_path(file_name);
  {
    // Hash the whole file.
    GrrMessage message;
    message.set_args(req.SerializeAsString());
    message.set_args_rdf_name("FingerprintRequest");

    ActionContext context(message, &queue, nullptr);
    action.ProcessRequest(&context);
    const auto r = queue.GetMessages(5, 20000, true);
    ASSERT_EQ(r.size(), 1);
    FingerprintResponse res;
    ASSERT_TRUE(res.ParseFromString(r[0].args()));
    EXPECT_EQ(BytesToHex(res.hash().md5()), "8867b7f850558298085205d03b823d1f");
    EXPECT_EQ(BytesToHex(res.hash().sha1()),
              "72022185a5d49398619aff380c50989e9946c7b9");
    EXPECT_EQ(
        BytesToHex(res.hash().sha256()),
        "2d3f76350c1db96e23e90d5ea05e6d1c3a78cf3c2a370e67da7d8d8f85cb57c6");
  }
  {
    // Hash the first sentance only.
    GrrMessage message;
    req.set_max_filesize(sizeof(kSentance) - 1);
    message.set_args(req.SerializeAsString());
    message.set_args_rdf_name("FingerprintRequest");

    ActionContext context(message, &queue, nullptr);
    action.ProcessRequest(&context);
    const auto r = queue.GetMessages(5, 20000, true);
    ASSERT_EQ(r.size(), 1);
    FingerprintResponse res;
    ASSERT_TRUE(res.ParseFromString(r[0].args()));
    EXPECT_EQ(BytesToHex(res.hash().md5()), "b261610902182c0581c791ac874f588c");
    EXPECT_EQ(BytesToHex(res.hash().sha1()),
              "87344ca7264d0f3e1d4e1350aeb71ffb597af8e2");
    EXPECT_EQ(
        BytesToHex(res.hash().sha256()),
        "4ef5816c41c74bcf9528330db5fe259c1fadec92c5318d18f8bb223a308f97e3");
  }
}
}  // namespace grr
