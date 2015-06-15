#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_

#include <memory>
#include <map>
#include <set>

#include "grr/proto/sysinfo.pb.h"
#include "../client_action.h"

namespace grr {
class EnumerateFilesystems : public ClientAction {
 public:
  EnumerateFilesystems();

  const char* Name() override { return kName; }

  void ProcessRequest(ActionContext* args) override;

  /*** Implementation details, public to support testing. ***/

  // Map from mount point to a filesystem record for it.
  typedef std::map<std::string, Filesystem> ResultMap;

  // Open and process the named file. Each filesystem is added to result if we
  // haven't already found a filesystem for that mount point, so the first entry
  // has priority.
  void ProcessFile(const std::string& filename, ResultMap* results);

 private:
  Filesystem ProcessLine(std::string line);

  static const char kName[];
  const std::set<std::string> to_report_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_FILESYSTEMS_H_
