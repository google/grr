#include "grr/client/minicomm/client_actions/enumerate_filesystems.h"

#include <fstream>
#include <sstream>

#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {

EnumerateFilesystems::EnumerateFilesystems()
    : to_report_{"ext2",  "ext3",     "ext4", "vfat", "ntfs",
                 "btrfs", "Reiserfs", "XFS",  "JFS",  "squashfs"} {}

void EnumerateFilesystems::ProcessRequest(ActionContext* context) {
  ResultMap results;
  ProcessFile("/proc/mounts", &results);
  ProcessFile("/etc/mtab", &results);

  for (const auto& p : results) {
    context->SendResponse(p.second, GrrMessage::MESSAGE);
  }
}

void EnumerateFilesystems::ProcessFile(const std::string& filename,
                                       ResultMap* results) {
  std::ifstream file(filename);
  if (!file.good()) {
    return;
  }
  std::string line;
  while (std::getline(file, line)) {
    Filesystem f = ProcessLine(line);
    if (f.has_mount_point()) {
      auto& result = (*results)[f.mount_point()];
      // Only use result if it is new - give the first record of the mount point
      // priority.
      if (result.mount_point() == "") {
        result = std::move(f);
      }
    }
  }
}

Filesystem EnumerateFilesystems::ProcessLine(std::string line) {
  Filesystem f;
  // Cut off any comments.
  const auto comment_pos = line.find("#");
  if (comment_pos != std::string::npos) {
    line = line.substr(0, comment_pos);
  }

  // Tokenize the rest, using the default istream whitespace setting.
  std::istringstream tokens(line);
  std::string device, mnt, fs;
  tokens >> device >> mnt >> fs;
  if (!tokens.fail() && to_report_.count(fs)) {
    f.set_device(device);
    f.set_mount_point(mnt);
    f.set_type(fs);
  }
  return f;
}
}  // namespace actions
}  // namespace grr
