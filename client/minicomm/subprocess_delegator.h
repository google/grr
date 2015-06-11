#ifndef GRR_CLIENT_MINICOMM_SUBPROCESS_DELEGATOR_H_
#define GRR_CLIENT_MINICOMM_SUBPROCESS_DELEGATOR_H_

#include <sys/types.h>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <thread>

#include "grr/client/minicomm/config.h"
#include "grr/client/minicomm/message_queue.h"
#include "google/protobuf/io/coded_stream.h"
#include "google/protobuf/io/zero_copy_stream.h"
#include "google/protobuf/io/zero_copy_stream_impl.h"

namespace grr {
// Creates a subprocess to handle messages.
class SubprocessDelegator {
 public:
  SubprocessDelegator(ClientConfig* config, MessageQueue* inbox,
                      MessageQueue* outbox);
  ~SubprocessDelegator();

 private:
  ClientConfig* config_;
  MessageQueue* inbox_;
  MessageQueue* outbox_;

  // PID of the child process. 0 indicates that no child process currently
  // exists. -1 indicates that the class is being destructed and that internal
  // threads need to exit.

  std::mutex child_pid_mutex_;
  pid_t child_pid_;
  std::condition_variable child_spawned_;

  // Vector of child pids which we have killed, but are so far unable
  // to reap.  Also protected by child_pit_mutex_.
  std::vector<pid_t> undead_children_;

  // Each of the following blocks contain structures used to manage a
  // communication channel with the subprocess. The *Loop methods access these
  // and rely on the following invariants:
  //
  // 1) The *stream_ pointers are non-null when child_pid_ > 0.
  // 2) The *stream_ pointers and pointees are protected by their
  //    respective mutexes.
  //
  // The (Start|Kill)Process methods assume that the *Loop methods will release
  // their corresponding mutexes shortly after a child is killed and then wait
  // until child_pid_ becomes non-zero.

  // Components to write commands to the subprocess.
  std::thread writer_thread_;
  std::mutex write_mutex_;
  std::unique_ptr<google::protobuf::io::FileOutputStream> write_stream_;

  // Components to read data from the subprocess.
  std::thread reader_thread_;
  std::mutex read_mutex_;
  std::unique_ptr<google::protobuf::io::FileInputStream> read_stream_;

  // Components to read errors from the subprocess.
  std::thread error_thread_;
  std::mutex error_mutex_;
  std::unique_ptr<google::protobuf::io::FileInputStream> error_stream_;

  void StartChildProcess();
  void KillChildProcess();

  // Loops to write to and read from child process. Executed by *thread_. Will
  // repeated until child_pid_ becomes -1.
  void WriteLoop();
  void ReadLoop();
  void ErrorLoop();
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_SUBPROCESS_DELEGATOR_H_
