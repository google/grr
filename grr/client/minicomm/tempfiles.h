#ifndef GRR_CLIENT_MINICOMM_TEMPFILES_H_
#define GRR_CLIENT_MINICOMM_TEMPFILES_H_

#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <memory>
#include <string>

#include "grr/client/minicomm/config.h"

namespace grr {
class TemporaryFiles {
 public:
  explicit TemporaryFiles(const ClientConfig& config) : config_(config) {}

  // If the path is a directory, and directory is inside the temporary
  // directory specified by the ClientConfig then everything in the directory is
  // deleted. In case path is a file, and if that file is inside the temporary
  // directory specified by the ClientConfig, it gets deleted.
  // Files which have been deleted and have not been deleted are logged to log.
  // Returns true on success, and false on failure, in which case error gets
  // populated with error information.
  bool DeleteGRRTempFiles(const std::string& path, std::string* const log,
                          std::string* const error);

  // Create a new temporary file in the temporary directory with filename
  // prefix.
  // Returns path to the created file on success, else returns empty string and
  // error gets populated.
  std::string CreateGRRTempFile(const std::string& prefix,
                                std::string* const error);

 private:
  const ClientConfig& config_;
  bool DeleteGRRTempFile(const std::string& path);
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_TEMPFILES_H_
