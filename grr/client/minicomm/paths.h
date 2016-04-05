#ifndef GRR_CLIENT_MINICOMM_PATHS_H_
#define GRR_CLIENT_MINICOMM_PATHS_H_

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/file_operations.h"

namespace grr {
class Paths {
 public:
  // Attempts to normalize spec and open the resulting path. If successful,
  // adjusts it in place and returns true. Otherwise sets error and returns
  // nullptr.
  static std::unique_ptr<OpenedPath> NormalizeAndOpen(PathSpec* spec,
                                                      std::string* error);

 private:
  static std::unique_ptr<OpenedPath> TryOpenFromRoot(
      std::unique_ptr<OpenedPath> root, const PathSpec& spec,
      std::string* error);
  static std::unique_ptr<OpenedPath> TryExtendLiteral(
      std::unique_ptr<OpenedPath> path, const std::string& component,
      std::string* error);
  static std::unique_ptr<OpenedPath> TryExtendInsensitive(
      std::unique_ptr<OpenedPath> path, const std::string& component,
      std::string* error);
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_PATHS_H_
