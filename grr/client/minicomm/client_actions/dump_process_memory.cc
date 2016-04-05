#include "grr/client/minicomm/client_actions/dump_process_memory.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/wait.h>

#include <memory>

#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/paths.h"
#include "grr/client/minicomm/tempfiles.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {
void DumpProcessMemory::ProcessRequest(ActionContext *context) {
  DumpProcessMemoryRequest req;
  if (!context->PopulateArgs(&req)) {
    return;
  }

  PathSpec res;
  const int pid = req.pid();
  const bool pause = req.pause();
  std::string error;

  std::string dump_location = DumpImage(pid, pause, &error, context->Config());
  if (dump_location.size() > 0) {
    res.set_path(dump_location);
    res.set_pathtype(PathSpec::OS);
    context->SendResponse(res, GrrMessage::MESSAGE);
  } else {
    context->SetError(error);
  }
}

std::string DumpProcessMemory::DumpImage(const int pid, const bool pause,
                                         std::string *const error,
                                         const ClientConfig &config) const {
  ProcessAttachmentHandle handle(pid, pause, error, config);
  if (handle.good() == false) {
    return std::string();
  }

  std::string line;

  // Maximum size of the buffer should not be larger than 512KiB.
  const int MAXBUFF = 512 * 1024;
  char buff[MAXBUFF];

  while (std::getline(handle.MapsHandle(), line)) {
    uint64 a, b;
    std::istringstream line_stream(line);
    std::string range, permissions, junk, filehandle;
    line_stream >> range >> permissions >> junk >> junk >> filehandle;
    std::istringstream range_stream(range);
    char junk_chr;
    range_stream >> std::hex >> a >> junk_chr >> std::hex >> b;
    if (range_stream.fail()) continue;

    // If the region is not readable, skip it.
    if (permissions[0] != 'r') continue;
    // If the file is mapped to this region don't aquire it.
    if (filehandle[0] != '0') continue;

    if (a >= b) continue;

    int64 offset = a;
    if (lseek64(handle.MemHandle(), offset, SEEK_SET) != offset) continue;

    while (offset < b) {
      const int size =
          static_cast<int>(std::min(b - offset, static_cast<uint64>(MAXBUFF)));
      int len = read(handle.MemHandle(), buff, size);
      if (len <= 0) break;
      if (write(handle.DumpHandle(), buff, len) == -1) {
        *error += "Unable to write memory to file." + ErrorName(errno) + "\n";
        return std::string();
      }
      offset += len;
    }
  }

  return handle.TempFileLocation();
}

DumpProcessMemory::ProcessAttachmentHandle::ProcessAttachmentHandle(
    const int pid, const bool pause, std::string *const error,
    const ClientConfig &config)
    : pid_(pid), error_(error), pause_(pause), mem_(error), dump_(error) {
  TemporaryFiles temp_files(config);
  std::ostringstream mem_file_name;
  mem_file_name << "/proc/" << pid << "/mem";

  std::ostringstream maps_file_name;
  maps_file_name << "/proc/" << pid << "/maps";

  mem_.set_fd(open(mem_file_name.str().c_str(), O_RDONLY));

  if (mem_.get_fd() == -1) {
    *error += "Could not open /proc/pid/mem.\n";
    return;
  }

  const std::string prefix = "DumpProcessMemory";
  temp_file_path_ = temp_files.CreateGRRTempFile(prefix, error);
  if (temp_file_path_.size()) {
    dump_.set_fd(open(temp_file_path_.c_str(), O_RDWR));
    if (dump_.get_fd() == -1) {
      *error += "Could not open temporary file.\n";
      return;
    }
  } else {
    *error += "Could not create a temporary file.\n";
    return;
  }

  maps_stream_.open(maps_file_name.str());
  if (maps_stream_.good() == false) {
    *error += "Could not open /proc/pid/maps.\n";
    return;
  }

  if (pause_) {
    // Process shouldn't try to pause itself.
    if (getpid() == pid_) {
      *error += "This process can't pause itself.\n";
      return;
    } else {
      if (ptrace(PTRACE_ATTACH, pid_, NULL, NULL) != 0) {
        *error += "Unable to attach to process.\n";
        return;
      }
      if (waitpid(pid_, NULL, 0) != pid_) {
        *error += "Process did not change state.\n";
        return;
      }
      paused_ = true;
    }
  }
}

DumpProcessMemory::ProcessAttachmentHandle::~ProcessAttachmentHandle() {
  if (paused_) {
    if (ptrace(PTRACE_DETACH, pid_, NULL, NULL) != 0) {
      *error_ += "Could not unpause the process.\n";
    }
  }
}

bool DumpProcessMemory::ProcessAttachmentHandle::good() const {
  if (mem_.get_fd() == -1) return false;
  if (dump_.get_fd() == -1) return false;
  if (paused_ != pause_) return false;
  if (maps_stream_.good() == false) return false;
  return true;
}

}  // namespace actions
}  // namespace grr
