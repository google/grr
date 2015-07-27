#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_TRANSFER_BUFFER_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_TRANSFER_BUFFER_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class TransferBuffer : public ClientAction {
 public:
  TransferBuffer() {}

  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr
#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_TRANSFER_BUFFER_H_
