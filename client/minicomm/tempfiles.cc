#include "grr/client/minicomm/tempfiles.h"

#include <libgen.h>
#include <linux/limits.h>
#include <sys/types.h>

#include <vector>

#include "grr/client/minicomm/paths.h"

namespace grr {
namespace {
std::string NormalizePath(const std::string str) {
  char buffer[PATH_MAX];
  if (realpath(str.c_str(), buffer) == buffer) {
    return std::string(buffer);
  } else {
    return std::string();
  }
}
}  // namespace

std::string TemporaryFiles::CreateGRRTempFile(const std::string& prefix,
                                              std::string* const error) {
  std::string location;
  location = NormalizePath(config_.TemporaryDirectory()) + "/" + prefix +
             ".XXXXXX" + '\0';
  if (location.size() == 0) {
    *error += "Unable to expand path while creating a temporary file.\n";
    return std::string();
  }

  std::unique_ptr<char[]> location_mutable(new char[location.size()]);
  std::copy(location.begin(), location.end(), location_mutable.get());
  int fd = mkstemp(location_mutable.get());

  if (fd == -1) {
    *error += "Unable to create temporary file descriptor.\n";
    return std::string();
  }

  if (close(fd) == -1) {
    *error += "Unable to close temporary file descriptor.\n";
    return std::string();
  }

  // Terminating character should not be included when returning the location to
  // the file.
  return std::string(location_mutable.get(), location.size() - 1);
}

bool TemporaryFiles::DeleteGRRTempFiles(const std::string& path,
                                        std::string* const log,
                                        std::string* const error) {
  auto handle = OpenedPath::Open(path, error);
  if (handle == nullptr) {
    *error += "Unable to open path.\n";
    return false;
  }

  std::vector<std::string> deleted;
  std::vector<std::string> not_deleted;
  if (handle->is_directory()) {
    std::string base_path = handle->Path();
    OpenedPath::Directory dir;
    if (!OpenedPath::ReadDirectory(std::move(handle), &dir, error)) {
      *error += "Unable to open directory.\n";
      return false;
    }

    for (const auto& d : dir) {
      if (d.first == "." || d.first == "..") {
        continue;
      }

      auto child_path = OpenedPath::Open(base_path + "/" + d.first, error);
      if (child_path == nullptr) {
        continue;
      }

      if (DeleteGRRTempFile(child_path->Path())) {
        deleted.emplace_back(child_path->Path());
      } else {
        not_deleted.emplace_back(child_path->Path());
      }
    }
  } else {
    if (DeleteGRRTempFile(handle->Path())) {
      deleted.emplace_back(handle->Path());
    } else {
      not_deleted.emplace_back(handle->Path());
    }
  }

  if (deleted.size()) {
    *log += "Deleted: \n";
    for (auto file : deleted) {
      *log += file + "\n";
    }
  }

  if (not_deleted.size()) {
    *log += "Not deleted: \n";
    for (auto file : not_deleted) {
      *log += file + "\n";
    }
  }

  return true;
}

bool TemporaryFiles::DeleteGRRTempFile(const std::string& path) {
  const std::string normalized_path = NormalizePath(path);

  if (normalized_path.size() > 0) {
    const std::string temp_path_prefix =
        NormalizePath(config_.TemporaryDirectory()) + "/";
    if (normalized_path.substr(0, temp_path_prefix.size()) !=
        temp_path_prefix) {
      return false;
    }

    if (remove(normalized_path.c_str()) == 0) {
      return true;
    } else {
      return false;
    }
  } else {
    return false;
  }
}

}  // namespace grr
