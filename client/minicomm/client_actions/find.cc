#include "grr/client/minicomm/client_actions/find.h"

#include "grr/client/minicomm/paths.h"

#include "boost/regex.hpp"

namespace grr {
namespace actions {
void Find::ProcessRequest(ActionContext* context) {
  FindSpec req;
  if (!context->PopulateArgs(&req)) {
    return;
  }
  if (req.max_depth() == 0) {
    context->SetError("Max depth of 0.");
    return;
  }
  if (req.has_path_glob() && !req.has_path_regex()) {
    context->SetError("Path glob not supported.");
    return;
  }

  std::string error;
  auto base = Paths::NormalizeAndOpen(req.mutable_pathspec(), &error);
  if (base == nullptr) {
    context->SetError(error);
    return;
  }

  if (!base->is_directory()) {
    context->SetError("Find pathspec is not a directory:[" + base->Path() +
                      "]");
    return;
  }
  std::vector<FileFilter> filters;

  std::unique_ptr<boost::regex> pattern;
  if (req.has_path_regex()) {
    pattern.reset(new boost::regex(req.path_regex(),
                                   boost::regex_constants::ECMAScript |
                                       boost::regex_constants::no_except));
    if (pattern->status()) {
      context->SetError("Unable to parse regex [" + req.path_regex() + "]");
      return;
    }
    filters.emplace_back([&pattern](const std::string name, const StatEntry&) {
      return !regex_match(name, *pattern);
    });
  }

  if (req.has_min_file_size()) {
    filters.emplace_back([&req](const std::string, const StatEntry& stats) {
      return stats.has_st_size() && req.min_file_size() > stats.st_size();
    });
  }
  if (req.has_max_file_size()) {
    filters.emplace_back([&req](const std::string, const StatEntry& stats) {
      return stats.has_st_size() && req.max_file_size() < stats.st_size();
    });
  }
  if (req.has_perm_mode()) {
    filters.emplace_back([&req](const std::string, const StatEntry& stats) {
      return stats.has_st_mode() &&
             (req.perm_mask() & stats.st_mode() != req.perm_mode());
    });
  }
  if (req.has_uid()) {
    filters.emplace_back([&req](const std::string, const StatEntry& stats) {
      return stats.has_st_uid() && req.uid() != stats.st_uid();
    });
  }
  if (req.has_gid()) {
    filters.emplace_back([&req](const std::string, const StatEntry& stats) {
      return stats.has_st_gid() && req.gid() != stats.st_gid();
    });
  }

  ProcessRecursive(filters, std::move(base), req.max_depth(), req.cross_devs(),
                   context);

  Iterator terminator = req.iterator();
  terminator.set_state(Iterator::FINISHED);
  context->SendResponse(terminator, GrrMessage::ITERATOR);
}

typedef std::function<bool(const std::string&, const StatEntry&)> FileFilter;

bool Find::ProcessRecursive(const std::vector<FileFilter>& filters,
                            std::unique_ptr<OpenedPath> path,
                            int remaining_depth, bool cross_devices,
                            ActionContext* context) {
  if (remaining_depth == 0) {
    context->SetError("Internal error: reached depth 0");
    return false;
  }
  if (path == nullptr || !path->is_directory()) {
    context->SetError(
        "Internal error: recursive path not open or not directory.");
    return false;
  }
  const StatEntry base_stats = path->Stats();
  const std::string base_path = path->Path();
  OpenedPath::Directory dir;
  std::string error;
  if (!OpenedPath::ReadDirectory(std::move(path), &dir, &error)) {
    context->SetError(error);
    return false;
  }
  for (const auto& d : dir) {
    if (d.first == "." || d.first == "..") {
      continue;
    }
    auto child_path = OpenedPath::Open(base_path + "/" + d.first, &error);
    if (child_path != nullptr) {
      const StatEntry child_stats = child_path->Stats();
      bool filtered = false;
      for (const auto& f : filters) {
        if (f(d.first, child_stats)) {
          filtered = true;
          break;
        }
      }
      if (!filtered) {
        FindSpec res;
        *res.mutable_hit() = child_stats;
        res.mutable_hit()->mutable_pathspec()->set_path(child_path->Path());
        res.mutable_hit()->mutable_pathspec()->set_pathtype(PathSpec::OS);
        context->SendResponse(res, GrrMessage::MESSAGE);
      }
      if (remaining_depth > 2 && child_path->is_directory() &&
          (cross_devices || (child_stats.st_dev() == base_stats.st_dev()))) {
        ProcessRecursive(filters, std::move(child_path), remaining_depth - 1,
                         cross_devices, context);
      }
    }
  }
}
}  // namespace actions
}  // namespace grr
