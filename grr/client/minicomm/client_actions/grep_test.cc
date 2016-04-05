#include "grr/client/minicomm/client_actions/grep.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/test_util.h"

namespace grr {
namespace actions {

TEST(GrepTest, SimpleLiteralSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  std::ofstream file;
  file.open(file_name);
  file << R"(The quick sly fox jumped over the lazy dogs.)";
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(0);
  spec.set_literal("fox");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(1, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;
  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  EXPECT_EQ(14, res.offset());
  EXPECT_EQ(3, res.length());
}

TEST(GrepTest, MultipleHitLiteralSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  static const char kSentance[] =
      "The quick sly fox jumped over the lazy dogs. ";
  std::ofstream file;
  file.open(file_name);
  for (int i = 0; i < 5; i++) {
    file << kSentance;
  }
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(0);
  spec.set_literal("fox");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(5, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;

  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  EXPECT_EQ(14, res.offset());
  EXPECT_EQ(3, res.length());

  ASSERT_TRUE(res.ParseFromString(r[1].args()));
  EXPECT_EQ(14 + (sizeof(kSentance) - 1), res.offset());
  EXPECT_EQ(3, res.length());

  ASSERT_TRUE(res.ParseFromString(r[4].args()));
  EXPECT_EQ(14 + 4 * (sizeof(kSentance) - 1), res.offset());
  EXPECT_EQ(3, res.length());
}

TEST(GrepTest, FirstHitLiteralSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  static const char kSentance[] =
      "The quick sly fox jumped over the lazy dogs. ";
  std::ofstream file;
  file.open(file_name);
  for (int i = 0; i < 5; i++) {
    file << kSentance;
  }
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(0);
  spec.set_mode(GrepSpec::FIRST_HIT);
  spec.set_literal("fox");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(1, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;

  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  EXPECT_EQ(14, res.offset());
  EXPECT_EQ(3, res.length());
}

TEST(GrepTest, BytesBeforeLiteralSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  static const char kSentance[] =
      "The quick sly fox jumped over the lazy dogs. ";
  std::ofstream file;
  file.open(file_name);
  for (int i = 0; i < 5; i++) {
    file << kSentance;
  }
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(20);
  spec.set_bytes_after(0);
  spec.set_literal("fox");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(5, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;

  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  // Offset should be bounded at 0.
  EXPECT_EQ(0, res.offset());
  EXPECT_EQ(17, res.length());

  ASSERT_TRUE(res.ParseFromString(r[1].args()));
  EXPECT_EQ(14 + (sizeof(kSentance) - 1) - 20, res.offset());
  EXPECT_EQ(23, res.length());

  ASSERT_TRUE(res.ParseFromString(r[4].args()));
  EXPECT_EQ(14 + 4 * (sizeof(kSentance) - 1) - 20, res.offset());
  EXPECT_EQ(23, res.length());
}

TEST(GrepTest, BytesAfterLiteralSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  static const char kSentance[] =
      "The quick sly fox jumped over the lazy dogs. ";
  std::ofstream file;
  file.open(file_name);
  for (int i = 0; i < 5; i++) {
    file << kSentance;
  }
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(10);
  spec.set_literal("dogs");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(5, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;

  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  EXPECT_EQ(39, res.offset());
  EXPECT_EQ(14, res.length());

  ASSERT_TRUE(res.ParseFromString(r[4].args()));
  EXPECT_EQ(39 + 4 * (sizeof(kSentance) - 1), res.offset());
  // The file ends 6 characters after the start of the last occurence of dogs.
  EXPECT_EQ(6, res.length());
}

TEST(GrepTest, SimpleRegexSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  std::ofstream file;
  file.open(file_name);
  file << R"(The quick sly fox jumped over the lazy dogs.)";
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(0);
  spec.set_regex("fox");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(1, r.size());
  EXPECT_EQ("BufferReference", r[0].args_rdf_name());
  BufferReference res;
  ASSERT_TRUE(res.ParseFromString(r[0].args()));
  EXPECT_EQ(14, res.offset());
  EXPECT_EQ(3, res.length());
}

TEST(GrepTest, BrokenRegexSearch) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/fox.txt";
  std::ofstream file;
  file.open(file_name);
  file << R"(The quick sly fox jumped over the lazy dogs.)";
  file.close();

  GrepSpec spec;
  spec.mutable_target()->set_path(file_name);
  spec.mutable_target()->set_pathtype(PathSpec::OS);
  spec.set_bytes_before(0);
  spec.set_bytes_after(0);
  spec.set_regex("fo[x(])");

  GrrMessage message;
  message.set_args(spec.SerializeAsString());
  message.set_args_rdf_name("GrepSpec");

  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  Grep action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, false);
  EXPECT_EQ(0, r.size());
  EXPECT_EQ(GrrStatus::GENERIC_ERROR, context.Status().status());
  GOOGLE_LOG(INFO) << context.Status().DebugString();
}
}  // namespace actions
}  // namespace grr
