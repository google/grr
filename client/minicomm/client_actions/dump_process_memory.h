#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DUMP_PROCESS_MEMORY_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DUMP_PROCESS_MEMORY_H_

#include <unistd.h>

#include <fstream>
#include <iostream>
#include <string>
#include <sstream>

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class DumpProcessMemory : public ClientAction {
 public:
  DumpProcessMemory() {}

  void ProcessRequest(ActionContext* args) override;
  class ProcessAttachmentHandle {
   public:
    ProcessAttachmentHandle(const int, const bool, std::string* const error,
                            const ClientConfig&);
    ~ProcessAttachmentHandle();

    bool good() const;
    int MemHandle() const { return mem_.get_fd(); }
    int DumpHandle() const { return dump_.get_fd(); }
    std::ifstream& MapsHandle() { return maps_stream_; }
    std::string TempFileLocation() { return temp_file_path_; }

   private:
    class FileHandle {
     public:
      explicit FileHandle(std::string* const error) : fd_(-1), error_(error) {}
      ~FileHandle() { close_fd(); }

      int get_fd() const { return fd_; }
      void set_fd(int fd) {
        close_fd();
        fd_ = fd;
      }

     private:
      void close_fd() {
        if (fd_ != -1) {
          if (close(fd_) != 0) {
            if (error_ != nullptr) {
              *error_ += "Could not close file descriptor.\n";
            }
          } else {
            fd_ = -1;
          }
        }
      }

      int fd_;
      std::string* const error_;
    };

    const int pid_;
    const bool pause_;

    bool paused_ = 0;

    FileHandle mem_;
    FileHandle dump_;

    std::string temp_file_path_;
    std::string* const error_;
    std::ifstream maps_stream_;
  };

 private:
  std::string DumpImage(const int, const bool, std::string* const,
                        const ClientConfig&) const;
};

class DeleteFile : public ClientAction {
 public:
  DeleteFile() {}
  void ProcessRequest(ActionContext* args) override;
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_DUMP_PROCESS_MEMORY_H_
