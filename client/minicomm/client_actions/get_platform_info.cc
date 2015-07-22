#include "grr/client/minicomm/client_actions/get_platform_info.h"

#include <errno.h>
#include <netdb.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/utsname.h>
#include <unistd.h>

#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {
void GetPlatformInfo::ProcessRequest(ActionContext* context) {
  // Get what we can from uname.
  struct utsname result;
  if (uname(&result)) {
    context->SetError("Uname failed with errno: " + ErrorName(errno));
    return;
  }
  Uname response;
  response.set_system(ArrayToString(result.sysname));
  response.set_node(ArrayToString(result.nodename));
  response.set_kernel(ArrayToString(result.release));
  response.set_version(ArrayToString(result.version));
  response.set_machine(ArrayToString(result.machine));

  if (response.node().find(".") != std::string::npos) {
    response.set_fqdn(response.node());
  }

  // TODO(user): Add distribution detection.
  context->SendResponse(response, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
