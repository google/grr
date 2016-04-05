#include "grr/client/minicomm/client_actions/get_configuration.h"

#include "grr/proto/jobs.pb.h"

namespace grr {
namespace actions {

void GetConfiguration::ProcessRequest(ActionContext* context) {
  Dict res;
  context->SendResponse(res, GrrMessage::MESSAGE);
}

}  // namespace actions
}  // namespace grr
