#include "grr/client/minicomm/file_operations.h"

#include <algorithm>
#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/test_util.h"

namespace grr {
namespace {
void WriteFile(const std::string& filename, const std::string& contents) {
  std::ofstream file;
  file.open(filename);
  file << contents;
  file.close();
}
std::string UpperString(const std::string& s) {
  std::string r(s);
  std::transform(r.begin(), r.end(), r.begin(), ::toupper);
}
}  // namespace

TEST(FileOperations, ReadDirectory) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file1 = temp_dir + "/file1";
  WriteFile(file1, "File 1 contents.");
  const std::string file2 = temp_dir + "/file2";
  WriteFile(file2, "File 2 contents.");

  ASSERT_EQ(mkdir((temp_dir + "/subdir").c_str(), S_IRWXU), 0);

  std::string error;
  auto result = OpenedPath::Open(temp_dir, &error);
  ASSERT_TRUE(result != nullptr) << error;
  ASSERT_TRUE(result->is_directory());
  ASSERT_FALSE(result->is_regular());

  OpenedPath::Directory files;
  EXPECT_TRUE(OpenedPath::ReadDirectory(std::move(result), &files, &error))
      << error;

  typedef OpenedPath::FileType Type;
  ASSERT_EQ(files.size(), 5);  // ".", ".." + 3
  EXPECT_EQ(files["."], Type::DIRECTORY);
  EXPECT_EQ(files["file1"], Type::NORMAL);
  EXPECT_EQ(files["subdir"], Type::DIRECTORY);
}

TEST(FileOperations, Open) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file = temp_dir + "/file";
  const std::string kFileContents("File contents.");
  WriteFile(file, kFileContents);

  const std::string subdir = temp_dir + "/subdir";
  ASSERT_EQ(mkdir(subdir.c_str(), S_IRWXU), 0);

  // Opening a nonexistant path should fail.
  std::string error = "";
  EXPECT_EQ(OpenedPath::Open(temp_dir + "/missing_file", &error), nullptr);
  EXPECT_NE(error, "");

  // Open, stat should work.
  auto res = OpenedPath::Open(file, &error);
  ASSERT_NE(res, nullptr);
  EXPECT_TRUE(res->is_regular());
  EXPECT_FALSE(res->is_directory());

  StatEntry stat_result = res->Stats();
  EXPECT_EQ(stat_result.st_size(), kFileContents.size());
}

TEST(FileOperations, BadSeek) {
  const std::string temp_dir = testing::MakeTempDir();
  auto res = OpenedPath::Open(temp_dir, nullptr);
  ASSERT_NE(res, nullptr);

  std::string error;
  EXPECT_FALSE(res->Seek(-42, &error));
  GOOGLE_LOG(INFO) << error;
}

TEST(FileOperations, ReadSeek) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file = temp_dir + "/file";
  const std::string kFileContents = "Start67890" + std::string(1500, 'F') +
                                    "Middle7890" + std::string(1500, 'S') +
                                    "End4567890";
  WriteFile(file, kFileContents);

  std::string error;

  auto opened_file = OpenedPath::Open(file, &error);
  ASSERT_NE(opened_file, nullptr);

  // Start by reading into a buffer larger than the file.
  char large_buf[4096];
  size_t bytes_read;
  EXPECT_TRUE(opened_file->Read(large_buf, &bytes_read, &error));
  EXPECT_EQ(std::string(large_buf, bytes_read), kFileContents);

  // Now read it in smaller chunks.
  EXPECT_TRUE(opened_file->Seek(0, &error));
  std::string result;
  result.reserve(kFileContents.size());
  bytes_read = -1;
  char small_buf[64];
  while (bytes_read != 0) {
    ASSERT_TRUE(opened_file->Read(small_buf, &bytes_read, &error));
    result += std::string(small_buf, bytes_read);
  }
  EXPECT_EQ(result, kFileContents);

  // Now read the first part into a larger buffer.

  EXPECT_TRUE(opened_file->Seek(0, &error));
  EXPECT_TRUE(opened_file->Read(large_buf, 500, &bytes_read, &error));
  EXPECT_EQ(std::string(large_buf, bytes_read), kFileContents.substr(0, 500));

  // Seek to and read a small segment from the middle.
  EXPECT_TRUE(opened_file->Seek(1510, &error));
  EXPECT_TRUE(opened_file->Read(small_buf, 10, &bytes_read, &error));
  EXPECT_EQ(std::string(small_buf, bytes_read), "Middle7890");

  // Buffer size is a hard limit on bytes read.
  EXPECT_TRUE(opened_file->Read(small_buf, 128, &bytes_read, &error));
  EXPECT_EQ(bytes_read, 64);
}
}  // namespace grr
