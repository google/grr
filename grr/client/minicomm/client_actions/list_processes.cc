#include "grr/client/minicomm/client_actions/list_processes.h"

#include <unistd.h>
#include <fstream>
#include <sstream>

#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/paths.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {
void ListProcesses::ProcessRequest(ActionContext* context) {
  std::string error;
  auto result = OpenedPath::Open("/proc", &error);
  if (result == nullptr) {
    context->SetError(error);
    return;
  }

  OpenedPath::Directory dir;

  std::string base_path = result->Path();
  if (!OpenedPath::ReadDirectory(std::move(result), &dir, &error)) {
    context->SetError(error);
    return;
  }

  for (const auto& d : dir) {
    if (d.first == "." || d.first == ".." || IsNumber(d.first) == false) {
      continue;
    }

    const std::string procDir = base_path + "/" + d.first;
    Process res;
    if (PopulateProcessInfo(procDir, &res, &error) == false) {
      // maybe some more information can be given back to the server?
      continue;
    }

    context->SendResponse(res, GrrMessage::MESSAGE);
  }
}

bool ListProcesses::PopulateProcessInfo(const std::string& procDir,
                                        Process* res, std::string* error) {
  std::ifstream file(procDir + "/status");
  if (file.good() == true) {
    std::string line;
    while (std::getline(file, line)) {
      std::string field, data;
      const size_t pos = line.find(":");
      if (pos == std::string::npos) {
        continue;
      }

      field = line.substr(0, pos);
      data = line.substr(pos + 1, std::string::npos);
      const size_t trim_pos = data.find_first_not_of(" \t");

      if (trim_pos != std::string::npos)
        data = data.substr(trim_pos, std::string::npos);

      if (field == "Name") {
        res->set_name(data);
      }
      if (field == "Pid") {
        res->set_pid(strtol(data.c_str(), nullptr, 10));
      }
      if (field == "PPid") {
        res->set_ppid(strtol(data.c_str(), nullptr, 10));
      }
      if (field == "Threads") {
        res->set_num_threads(strtol(data.c_str(), nullptr, 10));
      }
    }
  } else {
    *error = "Error while reading process status.";
    return false;
  }

  file.close();
  file.open(procDir + "/cmdline");
  if (file.good() == true) {
    std::string arg;
    while (file.eof() == false) {
      const char c = file.get();
      if (c == 0) {
        if (arg.size() > 0) {
          res->add_cmdline(arg);
          arg.clear();
        }
      } else {
        arg += c;
      }
    }
  } else {
    *error = "Error while opening cmdline.";
    return false;
  }

  const std::string exeLocation = procDir + "/exe";
  const int size = 64 * 1024;
  static char buff[size];
  size_t read;
  const ssize_t sz = readlink(exeLocation.c_str(), buff, size);
  if (sz == -1) {
    *error = "Error while reading process location.";
    return false;
  } else {
    buff[sz] = 0;  // readlink does not return null-terminated strings
    res->set_exe(buff);
  }

  return true;
}

}  // namespace actions
}  // namespace grr
