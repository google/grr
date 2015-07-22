#include "grr/client/minicomm/client_actions/get_install_date.h"

#include "grr/client/minicomm/file_operations.h"

namespace grr {
namespace actions {
void GetInstallDate::ProcessRequest(ActionContext* context) {
  std::string error;
  auto result = OpenedPath::Open("/lost+found", &error);
  if (result == nullptr) {
    context->SetError(error);
    GOOGLE_LOG(ERROR) << "Unable to open lost+found: " << error;
    return;
  }
  DataBlob res;
  res.set_integer(result->Stats().st_ctime());
  GOOGLE_LOG(INFO) << "Returning: " << res.DebugString();
  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
