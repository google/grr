#include "grr/client/minicomm/file_operations.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "grr/client/minicomm/util.h"

#pragma pop_macro("st_atime")
#pragma pop_macro("st_ctime")
#pragma pop_macro("st_mtime")

#ifdef ANDROID
#include <sstream>
std::string to_string(off64_t t) {
  std::ostringstream os;
  os << t;
  return os.str();
}
#else
using std::to_string;
#endif

namespace grr {

OpenedPath::~OpenedPath() {
  if (fd_ != -1) {
    int result = close(fd_);
    if (result == -1) {
      GOOGLE_LOG(ERROR) << "Unable to close fd: " + ErrorName(errno);
    }
  }
}

namespace {
void SetError(const std::string& prefix, std::string* error) {
  if (error != nullptr) {
    *error = prefix + ": " + ErrorName(errno);
  }
}
}  // namespace

std::unique_ptr<OpenedPath> OpenedPath::Open(const std::string& path,
                                             std::string* error) {
  std::unique_ptr<OpenedPath> ret;
  const int fd =
      open(path.c_str(), O_RDONLY | O_NONBLOCK | O_LARGEFILE | O_CLOEXEC);
  if (fd == -1) {
    SetError("Unable to open [" + path + "]", error);
    return ret;
  }
  ret.reset(new OpenedPath(path, fd));
  const int stat_res = fstat64(fd, &ret->stat_);
  if (stat_res == -1) {
    SetError("Unable to stat [" + path + "]", error);
    ret.reset(nullptr);
    return ret;
  }
  if (ret->is_regular()) {
    const int fcntl_res = fcntl(fd, F_SETFD, O_NOATIME);
    if (fcntl_res == -1) {
      SetError("Unable to set noatime on regular file [" + path + "]", error);
      ret.reset(nullptr);
      return ret;
    }
  }
  return ret;
}

bool OpenedPath::Seek(uint64 offset, std::string* error) {
  const off64_t res = lseek64(fd_, offset, SEEK_SET);
  if (res == (off64_t)-1) {
    SetError("Unable to seek to [" + path_ + "] to [" + to_string(offset) + "]",
             error);
    return false;
  }
  return true;
}

uint64 OpenedPath::size() const { return stat_.st_size; }

bool OpenedPath::ReadInternal(char* buffer, size_t buffer_size,
                              size_t* bytes_read, std::string* error) {
  const ssize_t result = read(fd_, buffer, buffer_size);
  if (result == -1) {
    SetError("Unable to read [" + path_ + "]", error);
    return false;
  }
  *bytes_read = result;
  return true;
}

StatEntry OpenedPath::Stats() const {
  StatEntry stat_entry;
  stat_entry.set_st_mode(stat_.st_mode);
  stat_entry.set_st_ino(stat_.st_ino);
  stat_entry.set_st_dev(stat_.st_dev);
  stat_entry.set_st_nlink(stat_.st_nlink);
  stat_entry.set_st_uid(stat_.st_uid);
  stat_entry.set_st_gid(stat_.st_gid);
  stat_entry.set_st_size(stat_.st_size);
  stat_entry.set_st_atime(stat_.st_atime);
  stat_entry.set_st_mtime(stat_.st_mtime);
  stat_entry.set_st_ctime(stat_.st_ctime);
  stat_entry.set_st_blocks(stat_.st_blocks);
  stat_entry.set_st_blksize(stat_.st_blksize);
  stat_entry.set_st_rdev(stat_.st_rdev);
  return stat_entry;
}

bool OpenedPath::ReadDirectory(std::unique_ptr<OpenedPath> path,
                               OpenedPath::Directory* result,
                               std::string* error) {
  DIR* dir = fdopendir(path->fd_);
  if (dir == nullptr) {
    SetError("Unable to open as directory", error);
    return false;
  }
  errno = 0;
  while (struct dirent* ent = readdir(dir)) {
    FileType type;
    switch (ent->d_type) {
      case DT_BLK:
      case DT_REG:
        type = FileType::NORMAL;
        break;
      case DT_CHR:
      case DT_FIFO:
        type = FileType::STREAM;
        break;
      case DT_DIR:
        type = FileType::DIRECTORY;
        break;
      case DT_LNK:
        type = FileType::SYM_LINK;
        break;
      default:
        type = FileType::UNKNOWN;
    }
    (*result)[ArrayToString(ent->d_name)] = type;
  }
  if (errno) {
    SetError("Failure reading as directory [" + path->path_ + "]", error);
    closedir(dir);
    return false;
  }
  const int res = closedir(dir);
  if (res == -1) {
    SetError("Failure closing directory [" + path->path_ + "]", error);
    return false;
  }
  // closedir closed fd_, so ~OpenedPath doesn't need to.
  path->fd_ = -1;
  return true;
}

}  // namespace grr
