#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class FingerprintFile : public ClientAction {
 public:
  FingerprintFile() {}

  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_FINGERPRINT_FILE_H_
