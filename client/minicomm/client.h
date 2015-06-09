#ifndef GRR_CLIENT_MINICOMM_CLIENT_H_
#define GRR_CLIENT_MINICOMM_CLIENT_H_

#include <memory>
#include <string>

#include "comms_utils.h"
#include "config.h"
#include "http_connection.h"
#include "message_queue.h"
#include "subprocess_delegator.h"

namespace grr {

class Client {
 public:
  // Create a client configured by the config file referenced by filename.
  explicit Client(const std::string& filename);
  void Run();

  // Performs necessary static initialization. Must be called before any threads
  // are spawned.
  static void StaticInit();

 private:
  ClientConfig config_;

  MessageQueue inbox_;
  MessageQueue outbox_;

  HttpConnectionManager connection_manager_;
  std::unique_ptr<SecureSession> session_;

  SubprocessDelegator subprocess_delegator_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_H_
