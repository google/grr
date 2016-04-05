#include "grr/client/minicomm/paths.h"

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
}

TEST(Paths, NormalizePath) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file1 = temp_dir + "/file1";
  WriteFile(file1, "File 1 contents.");
  ASSERT_EQ(mkdir((temp_dir + "/subdir").c_str(), S_IRWXU), 0);
  const std::string file2 = temp_dir + "/subdir/file2";
  WriteFile(file2, "File 2 contents.");

  PathSpec spec;
  std::string error = "";
  spec.set_path(file1);
  spec.set_pathtype(PathSpec::OS);
  auto res = Paths::NormalizeAndOpen(&spec, &error);
  ASSERT_NE(res, nullptr);
  EXPECT_EQ(res->Path(), file1);
  EXPECT_EQ(spec.path(), file1);
  EXPECT_EQ(spec.path_options(), PathSpec::CASE_LITERAL);

  spec.set_path_options(PathSpec::CASE_INSENSITIVE);
  spec.set_path(temp_dir + "/SubDir/File2");

  res = Paths::NormalizeAndOpen(&spec, &error);
  ASSERT_NE(res, nullptr);
  EXPECT_EQ(res->Path(), file2);
  EXPECT_EQ(spec.path(), file2);
  EXPECT_EQ(spec.path_options(), PathSpec::CASE_LITERAL);
}
}  // namespace grr
