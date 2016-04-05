#include "grr/client/minicomm/client_actions/enumerate_filesystems.h"

#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/test_util.h"

namespace grr {
namespace actions {

TEST(EnumerateFilesystemsTest, ProcessFileNormal) {
  EnumerateFilesystems action;
  EnumerateFilesystems::ResultMap results;
  const std::string temp_dir = testing::MakeTempDir();

  const std::string file_name = temp_dir + "/fstab";
  std::ofstream file;
  file.open(file_name);
  file << R"(rootfs / rootfs rw 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
tmpfs /run tmpfs rw,nosuid,noexec,relatime,size=3285532k,mode=755 0 0
/dev/mapper/svg-root / ext4 rw,relatime,errors=remount-ro,i_version,
/dev/mapper/svg-usr+local+google /usr/local/google ext4 rw,relatime,i_version,data=writeback 0 0
/dev/sda1 /boot ext2 rw,relatime,i_version,stripe=4 0 0
)";
  file.close();
  action.ProcessFile(file_name, &results);

  EXPECT_EQ(3, results.size());

  EXPECT_EQ("/dev/mapper/svg-root", results["/"].device());
  EXPECT_EQ("/", results["/"].mount_point());
  EXPECT_EQ("ext4", results["/"].type());

  EXPECT_EQ("/dev/sda1", results["/boot"].device());
  EXPECT_EQ("/boot", results["/boot"].mount_point());
  EXPECT_EQ("ext2", results["/boot"].type());
}

TEST(EnumerateFilesystemsTest, ProcessFileComments) {
  EnumerateFilesystems action;
  EnumerateFilesystems::ResultMap results;
  const std::string temp_dir = testing::MakeTempDir();

  const std::string file_name = temp_dir + "/fstab";
  std::ofstream file;
  file.open(file_name);
  file << R"(#/dev/sdb1   /boot vfat
/dev/sdb1 /boot ext4
 /dev/sdb2 /home Reiserfs
/dev/sdb3 # ext4 misplace comment
/dev/sdb3 /mnt/windows ntfs)";
  file.close();
  action.ProcessFile(file_name, &results);

  EXPECT_EQ(3, results.size());

  EXPECT_EQ("/dev/sdb1", results["/boot"].device());
  EXPECT_EQ("/boot", results["/boot"].mount_point());
  EXPECT_EQ("ext4", results["/boot"].type());

  EXPECT_EQ("/dev/sdb2", results["/home"].device());
  EXPECT_EQ("/home", results["/home"].mount_point());
  EXPECT_EQ("Reiserfs", results["/home"].type());

  EXPECT_EQ("/dev/sdb3", results["/mnt/windows"].device());
  EXPECT_EQ("/mnt/windows", results["/mnt/windows"].mount_point());
  EXPECT_EQ("ntfs", results["/mnt/windows"].type());
}
}  // namespace actions
}  // namespace grr
