#ifndef GRR_CLIENT_MINICOMM_FILE_OPERATIONS_H_
#define GRR_CLIENT_MINICOMM_FILE_OPERATIONS_H_

#include <memory>
#include <vector>

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/base.h"

// Needs to come after jobs.pb.h due to name clash.
// TODO(user): Fix properly (put protos in namespace?).
#include <sys/stat.h>

namespace grr {

// Attempts to determine if path is a symlink. On success, returns true an sets
// *result to its target, or the empty string if it is not a symlink. On
// failure, returns false and sets *error.
static bool ReadLink(const std::string& path, std::string* target,
                     std::string* error);

// Represents a file or directory which has been opened.
class OpenedPath {
 public:
  ~OpenedPath();

  // Attempt to open and stat path. Will follow symlinks. On success, it returns
  // an object representing path. On failure it returns nullptr and sets *error.
  static std::unique_ptr<OpenedPath> Open(const std::string& path,
                                          std::string* error);

  // The stats we found during OpenPath.
  StatEntry Stats() const;

  // The size of the file contents.
  size_t size() const;

  // The exact path which was opened.
  const std::string& Path() const { return path_; }


  bool is_directory() const { return S_ISDIR(stat_.st_mode); }
  bool is_regular() const { return S_ISREG(stat_.st_mode); }

  /*** File handling. ***/

  // Attempt to seek the underlying file descriptor to offset bytes from the
  // start of the file. If unsuccessful, returns false and sets *error.
  bool Seek(uint64 offset, std::string* error);

  // Attempts to read into buffer. On success returns true and sets bytes_read
  // to the number of bytes read. If at EOF, returns true with 0 bytes read. In
  // case of any other failure, returns false and sets *error.
  template <size_t size>
  bool Read(char(&buffer)[size], size_t* bytes_read, std::string* error) {
    return ReadInternal(buffer, size, bytes_read, error);
  }

  // Attempts to read up to limit bytes into buffer. On success returns true and
  // sets bytes_read to the number of bytes read. If at EOF, returns true with 0
  // bytes read. In case of any other failure, returns false and sets *error.
  template <size_t size>
  bool Read(char(&buffer)[size], size_t limit, size_t* bytes_read,
            std::string* error) {
    return ReadInternal(buffer, std::min(size, limit), bytes_read, error);
  }

  // Attempts to mmap file. On success returns a pointers to the start of the
  // file contents. Only maps this.size() bytes. Mapping is valid for the
  // lifspan of this object.
  //
  // Warning: It is possible to segfault on access if a file is truncated after
  // being mmapped. TODO(user): Replace this with a more stable random
  // access method.
  const char* MMap(std::string* error);

  /*** Directory handling ***/

  enum class FileType { NORMAL, STREAM, DIRECTORY, SYM_LINK, UNKNOWN };

  // A map from filename to filetype.
  typedef std::map<std::string, FileType> Directory;

  // Attempt to read path as a directory. On success, returns true and populates
  // *dir.  On failure, returns false and sets *error. Closes and deletes path.
  static bool ReadDirectory(std::unique_ptr<OpenedPath> path, Directory* dir,
                            std::string* error);

 private:
  OpenedPath(const std::string& path, int fd)
      : path_(path), fd_(fd), mmap_loc_(nullptr) {}
  const std::string path_;
  int fd_;
  const char* mmap_loc_;
  struct stat stat_;

  bool ReadInternal(char* buffer, size_t buffer_size, size_t* bytes_read,
                    std::string* error);
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_FILE_OPERATIONS_H_
