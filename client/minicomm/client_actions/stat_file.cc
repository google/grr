#include "grr/client/minicomm/client_actions/stat_file.h"

#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {
void StatFile::ProcessRequest(ActionContext* context) {
  ListDirRequest req;
  if (!context->PopulateArgs(&req)) {
    return;
  }

  std::string error;
  auto result = Paths::NormalizeAndOpen(req.mutable_pathspec(), &error);
  if (result == nullptr) {
    context->SetError(error);
    return;
  }
  StatEntry res = result->Stats();
  *res.mutable_pathspec() = req.pathspec();
  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
