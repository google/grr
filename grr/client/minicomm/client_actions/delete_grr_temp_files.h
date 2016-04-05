#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DELETE_GRR_TEMP_FILES_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DELETE_GRR_TEMP_FILES_H_

#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <memory>
#include <string>

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class DeleteGRRTempFiles : public ClientAction {
 public:
  DeleteGRRTempFiles() {}
  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DELETE_GRR_TEMP_FILES_H_
