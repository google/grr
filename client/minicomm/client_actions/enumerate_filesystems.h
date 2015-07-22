#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_

#include <memory>
#include <map>
#include <set>

#include "grr/proto/sysinfo.pb.h"
#include "gtest/gtest_prod.h"
#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class EnumerateFilesystems : public ClientAction {
 public:
  EnumerateFilesystems();

  void ProcessRequest(ActionContext* args) override;

 private:
  // Map from mount point to a filesystem record for it.
  typedef std::map<std::string, Filesystem> ResultMap;

  // Open and process the named file. Each filesystem is added to result if we
  // haven't already found a filesystem for that mount point, so the first entry
  // has priority.
  void ProcessFile(const std::string& filename, ResultMap* results);

  Filesystem ProcessLine(std::string line);

  const std::set<std::string> to_report_;

  FRIEND_TEST(EnumerateFilesystemsTest, ProcessFileComments);
  FRIEND_TEST(EnumerateFilesystemsTest, ProcessFileNormal);
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_
