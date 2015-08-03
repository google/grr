#include "grr/client/minicomm/file_contents.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/test_util.h"
#include "boost/regex.hpp"

namespace grr {
TEST(FileContents, SmallFile) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/file_name";
  std::ofstream file;
  static const char kSentance[] =
      "The quick sly fox jumped over the lazy dogs.";
  file.open(file_name);
  file << kSentance;
  file.close();

  auto opened_file = OpenedPath::Open(file_name, nullptr);
  ASSERT_TRUE(opened_file != nullptr);

  FileContents c = FileContents(opened_file.get());
  FileContentsIterator i = c.begin();
  const FileContentsIterator end = c.end();

  i = c.begin();
  EXPECT_EQ('T', i[0]);
  EXPECT_EQ('e', i[2]);
  EXPECT_EQ('x', i[16]);

  EXPECT_EQ('T', *i);
  EXPECT_EQ('T', *i++);
  EXPECT_EQ('h', *i);
  EXPECT_EQ('e', *++i);
  EXPECT_EQ('e', *i);

  EXPECT_EQ('e', *i--);
  EXPECT_EQ('h', *i);
  EXPECT_EQ('T', *--i);
  EXPECT_EQ('T', *i);

  EXPECT_EQ('s', (i+10)[0]);
  EXPECT_TRUE(i+10 == (i+13)-3);

  std::string sentance_copy;
  sentance_copy.reserve(sizeof(kSentance));
  while (i != end) {
    sentance_copy.append(1, *i++);
  }
  EXPECT_EQ('.', i[-1]);
  EXPECT_EQ('s', i[-2]);

  EXPECT_EQ(kSentance, sentance_copy);
  EXPECT_EQ(sizeof(kSentance) - 1, c.end() - c.begin());
}

TEST(FileContents, LargeFile) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/haystack";
  const std::string kHay("hay");
  const int kHalfStack = 128 * 1024 / 3;
  const std::string kNeedle("needle");
  std::ofstream file;
  file.open(file_name);

  // This should put needle across the boundary of blocks 2 and 3.
  for (int i = 0; i < kHalfStack; i++) {
    file << kHay;
  }
  file << kNeedle;
  for (int i = 0; i < kHalfStack; i++) {
    file << kHay;
  }
  file << kNeedle;
  file.close();
  auto opened_file = OpenedPath::Open(file_name, nullptr);
  ASSERT_TRUE(opened_file != nullptr);

  FileContents c = FileContents(opened_file.get());
  auto found = std::search(c.begin(), c.end(), kNeedle.begin(), kNeedle.end());
  ASSERT_TRUE(found != c.end());
  for (int i = 0; i < kNeedle.size(); i++) {
    EXPECT_EQ(kNeedle[i], *found++);
  }

  // Look for a needle surrounded by hay, in a way that is likely to move
  // iterators forwards and backwards..
  boost::regex pattern(
      "(?<=hay)ne[eE][Dd]le(?=hay)",
      (boost::regex_constants::ECMAScript | boost::regex_constants::no_except));
  ASSERT_FALSE(pattern.status());

  typedef boost::regex_iterator<FileContentsIterator> regex_iterator;

  std::vector<std::string> results;
  for (auto i = regex_iterator(c.begin(), c.end(), pattern);
       i != regex_iterator(); ++i) {
    auto& m = *i;
    results.emplace_back(std::string(m[0].first, m[0].second));
  }
  ASSERT_EQ(results.size(), 1);
  EXPECT_EQ(results[0], "needle");

  // Count our hay.
  boost::regex hay_pattern("h.y");
  int hay_count = 0;
  for (auto i = regex_iterator(c.begin(), c.end(), hay_pattern);
       i != regex_iterator(); ++i) {
    hay_count += 1;
  }
  EXPECT_EQ(hay_count, 2 * kHalfStack);

  // This overflows, but should fail with a controlled exception, not with a
  // hard crash.
  boost::regex big_pattern("(hay)*needle(hay)*");
  ASSERT_THROW(regex_match(c.begin(), c.end(), big_pattern),
               std::runtime_error);
}

TEST(FileContents, TruncateFile) {
  const std::string temp_dir = testing::MakeTempDir();
  const std::string file_name = temp_dir + "/haystack";
  const std::string kHay("hay");
  std::ofstream file;
  file.open(file_name);
  for (int i = 0; i < 64 * 1024; i++) {
    file << kHay;
  }
  file.close();

  auto opened_file = OpenedPath::Open(file_name, nullptr);
  ASSERT_TRUE(opened_file != nullptr);
  FileContents c = FileContents(opened_file.get());

  // Our view of the file is now locked to 3 blocks of 64k, based on the initial
  // stat. If the underlying file is now resized, we see zero valued bytes where
  // the file isn't.
  ASSERT_EQ(0, truncate(file_name.c_str(), 3));

  EXPECT_EQ(c.begin()[0], 'h');
  EXPECT_EQ(c.begin()[1], 'a');
  EXPECT_EQ(c.begin()[2], 'y');
  EXPECT_EQ(c.begin()[3], '\0');
  EXPECT_EQ(c.begin()[2 * 64 * 1024], '\0');
  EXPECT_EQ(*--c.end(), '\0');
}
}  // namespace grr
