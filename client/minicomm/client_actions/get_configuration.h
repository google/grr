#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CONFIGURATION_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CONFIGURATION_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class GetConfiguration : public ClientAction {
 public:
  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_CONFIGURATION_H_
