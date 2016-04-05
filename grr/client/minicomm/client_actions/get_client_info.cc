#include "grr/client/minicomm/client_actions/get_client_info.h"

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/client_info.h"

namespace grr {
namespace actions {
void GetClientInfo::ProcessRequest(ActionContext* context) {
  ClientInformation res;
  res.set_client_name(client_info::kName);
  res.set_client_description(client_info::kDescription);
  res.set_build_time(std::string(client_info::kBuildDate) + " " +
                     client_info::kBuildTime);
  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
