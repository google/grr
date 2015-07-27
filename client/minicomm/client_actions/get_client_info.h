#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CLIENT_INFO_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CLIENT_INFO_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class GetClientInfo : public ClientAction {
 public:
  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CLIENT_INFO_H_
