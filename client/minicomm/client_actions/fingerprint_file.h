#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
class FingerprintFile : public ClientAction {
 public:
  FingerprintFile() {}

  void ProcessRequest(ActionContext* args) override;
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_
