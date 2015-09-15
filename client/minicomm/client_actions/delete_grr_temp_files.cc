#include "grr/client/minicomm/client_actions/delete_grr_temp_files.h"

#include <libgen.h>
#include <sys/types.h>

#include <vector>

#include "grr/client/minicomm/tempfiles.h"
#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {
void DeleteGRRTempFiles::ProcessRequest(ActionContext* context) {
  PathSpec req;
  if (!context->PopulateArgs(&req)) {
    return;
  }

  std::string error;
  std::string log;

  TemporaryFiles temp_files(context->Config());
  if (temp_files.DeleteGRRTempFiles(req.path(), &log, &error)) {
    PrintStr log_str;
    log_str.set_data(log);
    context->SendResponse(log_str, GrrMessage::MESSAGE);
  } else {
    context->SetError(error);
  }
}
}  // namespace actions
}  // namespace grr
