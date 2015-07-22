#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_USERS_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_USERS_H_

#include <vector>

#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class EnumerateUsers : public ClientAction {
 public:
  EnumerateUsers() {}

  void ProcessRequest(ActionContext* args) override;

 private:
  std::map<std::string, int32> UsersFromWtmp(const std::string& wtmp);
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_ENUMERATE_USERS_H_
