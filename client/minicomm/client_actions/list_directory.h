#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_DIRECTORY_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_DIRECTORY_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class ListDirectory : public ClientAction {
 public:
  ListDirectory() {}

  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_LIST_DIRECTORY_H_
