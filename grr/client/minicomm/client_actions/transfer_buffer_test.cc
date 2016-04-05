#include "grr/client/minicomm/client_actions/transfer_buffer.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/compression.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {

TEST(TransferBuffer, SmallFile) {
  const std::string temp_dir = testing::MakeTempDir();

  const std::string file_name = temp_dir + "/text";
  const char kText[] =
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
      "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
      "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
      "commodo consequat. Duis aute irure dolor in reprehenderit in voluptate "
      "velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
      "occaecat cupidatat non proident, sunt in culpa qui officia deserunt "
      "mollit anim id est laborum. ";

  std::ofstream file;
  file.open(file_name);
  file << kText;
  file.close();

  MessageQueue queue(5, 20000);
  actions::TransferBuffer action;

  BufferReference req;
  req.mutable_pathspec()->set_pathtype(PathSpec::OS);
  req.mutable_pathspec()->set_path(file_name);
  req.set_offset(0);
  req.set_length(sizeof(kText) - 1);

  {
    // Hash.
    GrrMessage message;
    message.set_args(req.SerializeAsString());
    message.set_args_rdf_name("BufferReference");
    message.set_name("HashBuffer");

    ActionContext context(message, &queue, nullptr);
    action.ProcessRequest(&context);
    const auto r = queue.GetMessages(5, 20000, true);
    ASSERT_EQ(r.size(), 1);

    BufferReference res;
    ASSERT_TRUE(res.ParseFromString(r[0].args()));
    EXPECT_EQ(0, res.offset());
    EXPECT_EQ(sizeof(kText) - 1, res.length());
    EXPECT_EQ(
        "cca04536113e16feaa3fe109e5410ca96ce51661476e12bf501ada46619069c1",
        BytesToHex(res.data()));
  }
  {
    // Transfer.
    GrrMessage message;
    message.set_args(req.SerializeAsString());
    message.set_args_rdf_name("BufferReference");
    message.set_name("TransferBuffer");

    ActionContext context(message, &queue, nullptr);
    action.ProcessRequest(&context);
    const auto r = queue.GetMessages(5, 20000, true);
    ASSERT_EQ(r.size(), 2);

    DataBlob blob;
    ASSERT_EQ("DataBlob", r[0].args_rdf_name());
    ASSERT_TRUE(blob.ParseFromString(r[0].args()));
    EXPECT_EQ(DataBlob::ZCOMPRESSION, blob.compression());
    EXPECT_EQ(kText, ZLib::Inflate(blob.data()));

    BufferReference res;
    ASSERT_EQ("BufferReference", r[1].args_rdf_name());
    ASSERT_TRUE(res.ParseFromString(r[1].args()));
    EXPECT_EQ(0, res.offset());
    EXPECT_EQ(sizeof(kText) - 1, res.length());
    EXPECT_EQ(
        "cca04536113e16feaa3fe109e5410ca96ce51661476e12bf501ada46619069c1",
        BytesToHex(res.data()));
  }
}
}  // namespace grr
