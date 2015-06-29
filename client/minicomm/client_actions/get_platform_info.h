#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_PLATFORM_INFO_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_PLATFORM_INFO_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
class GetPlatformInfo : public ClientAction {
 public:
  const char* Name() override { return kName; }

  void ProcessRequest(ActionContext* args) override;

 private:
  static const char kName[];
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GET_PLATFORM_INFO_H_
