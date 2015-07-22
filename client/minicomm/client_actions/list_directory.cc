#include "grr/client/minicomm/client_actions/list_directory.h"

#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {

void ListDirectory::ProcessRequest(ActionContext* context) {
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

  OpenedPath::Directory dir;

  std::string base_path = result->Path();
  if (!OpenedPath::ReadDirectory(std::move(result), &dir, &error)) {
    context->SetError(error);
    return;
  }

  for (const auto& d : dir) {
    if (d.first == "." || d.first == "..") {
      continue;
    }

    auto child_path = OpenedPath::Open(base_path + "/" + d.first, &error);
    if (child_path == nullptr) {
      continue;
    }

    StatEntry res = child_path->Stats();
    res.mutable_pathspec()->set_path(base_path + "/" + d.first);
    res.mutable_pathspec()->set_pathtype(PathSpec::OS);
    res.mutable_pathspec()->set_path_options(PathSpec::CASE_LITERAL);
    context->SendResponse(res, GrrMessage::MESSAGE);
  }
}
}  // namespace actions
}  // namespace grr
