#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_STAT_FILE_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_STAT_FILE_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class StatFile : public ClientAction {
 public:
  StatFile() {}

  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr
#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_STAT_FILE_H_
