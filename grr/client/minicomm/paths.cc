#include "grr/client/minicomm/paths.h"

#include <algorithm>
#include <sstream>

namespace grr {

namespace {
bool PathExists(const std::string& s) {
  auto f = OpenedPath::Open(s, nullptr);
  return f != nullptr;
}

std::string LowerString(const std::string& s) {
  std::string r(s);
  std::transform(r.begin(), r.end(), r.begin(), ::tolower);
  return r;
}

void SetError(const std::string& msg, std::string* error) {
  if (error != nullptr) {
    *error = msg;
  }
}

std::string ExtendPath(const std::string& path, const std::string& component) {
  return path + (path.back() == '/' ? "" : "/") + component;
}

std::vector<std::string> SplitPath(const std::string& path) {
  std::vector<std::string> components;
  std::string comp;
  std::stringstream stream(path);
  while (std::getline(stream, comp, '/')) {
    if (comp != "") {
      components.push_back(comp);
    }
  }
  return components;
}
}  // namespace

std::unique_ptr<OpenedPath> Paths::NormalizeAndOpen(PathSpec* spec,
                                                    std::string* error) {
  std::unique_ptr<OpenedPath> res = OpenedPath::Open("/", error);
  res = TryOpenFromRoot(std::move(res), *spec, error);

  if (res == nullptr) {
    return res;
  }

  spec->set_path(res->Path());
  spec->set_path_options(PathSpec::CASE_LITERAL);
  spec->clear_nested_path();
  return res;
}

// Attempt to open spec, starting with path as a root.
std::unique_ptr<OpenedPath> Paths::TryOpenFromRoot(
    std::unique_ptr<OpenedPath> path, const PathSpec& spec,
    std::string* error) {
  if (path == nullptr) {
    return nullptr;
  }
  if (spec.pathtype() != PathSpec::OS) {
    SetError(
        "Unsupported path type: " + PathSpec::PathType_Name(spec.pathtype()),
        error);
    return nullptr;
  }
  if (!spec.mount_point().empty()) {
    SetError("Non-standard mount points not supported.", error);
    return nullptr;
  }
  if (spec.offset()) {
    SetError("Offset is not supported.", error);
    return nullptr;
  }
  if (!(spec.path_options() == PathSpec::CASE_LITERAL ||
        spec.path_options() == PathSpec::CASE_INSENSITIVE)) {
    SetError("Unsupported path options: " +
                 PathSpec::Options_Name(spec.path_options()),
             error);
    return nullptr;
  }

  switch (spec.path_options()) {
    case PathSpec::CASE_LITERAL:
      path = TryExtendLiteral(std::move(path), spec.path(), error);
      break;
    case PathSpec::CASE_INSENSITIVE:
      auto comps = SplitPath(spec.path());
      for (const auto& c : comps) {
        path = TryExtendInsensitive(std::move(path), c, error);
        if (path == nullptr) {
          return nullptr;
        }
      }
      break;
  }
  if (spec.has_nested_path()) {
    return TryOpenFromRoot(std::move(path), spec.nested_path(), error);
  }
  return path;
}

// Attempt to extend path with component, which is taken to be one or more case
// literal path components.  If successful, returns the newly opened
// path. Otherwise returns nullptr and sets *error.
std::unique_ptr<OpenedPath> Paths::TryExtendLiteral(
    std::unique_ptr<OpenedPath> path, const std::string& components,
    std::string* error) {
  if (path == nullptr) {
    return nullptr;
  }
  if (!path->is_directory()) {
    SetError("Path [" + path->Path() + "] is not a directory.", error);
    return nullptr;
  }
  return OpenedPath::Open(ExtendPath(path->Path(), components), error);
}

// Attempt to extend path with component, which is taken to be a single,
// case-insesitive, path component. If successful, returns the newly opened
// path. Otherwise returns nullptr and sets *error.
std::unique_ptr<OpenedPath> Paths::TryExtendInsensitive(
    std::unique_ptr<OpenedPath> path, const std::string& component,
    std::string* error) {
  if (path == nullptr) {
    return nullptr;
  }
  const std::string current_path = path->Path();
  if (!path->is_directory()) {
    SetError("Path [" + path->Path() + "] is not a directory.", error);
    return nullptr;
  }
  OpenedPath::Directory d;
  if (!OpenedPath::ReadDirectory(std::move(path), &d, error)) {
    return nullptr;
  }
  // Prefer the case exact match, if present.
  if (d.count(component)) {
    return OpenedPath::Open(ExtendPath(current_path, component), error);
  }
  // Take the first case insenstive match.
  std::string lowered_component = LowerString(component);
  for (const auto& p : d) {
    if (LowerString(p.first) == lowered_component) {
      return OpenedPath::Open(ExtendPath(current_path, p.first), error);
    }
  }
  SetError("Unable to find [" + component + "] in [" + current_path + "]",
           error);
  return nullptr;
}
}  // namespace grr
