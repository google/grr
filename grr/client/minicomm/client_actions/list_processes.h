#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_PROCESSES_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_PROCESSES_H_

#include "grr/proto/sysinfo.pb.h"
#include "gtest/gtest_prod.h"
#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {
class ListProcesses : public ClientAction {
 public:
  ListProcesses() {}

  void ProcessRequest(ActionContext* args) override;

 private:
  bool PopulateProcessInfo(const std::string& procDir, Process* res,
                           std::string* error);
  FRIEND_TEST(ListProcessesTest, PopulateProcessInfo);
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_PROCESSES_H_
