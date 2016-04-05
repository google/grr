#ifndef GRR_CLIENT_MINICOMM_CLIENT_H_
#define GRR_CLIENT_MINICOMM_CLIENT_H_

#include <memory>
#include <string>

#include "grr/client/minicomm/client_action_dispatcher.h"
#include "grr/client/minicomm/comms_utils.h"
#include "grr/client/minicomm/config.h"
#include "grr/client/minicomm/http_connection.h"
#include "grr/client/minicomm/message_queue.h"

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

  ClientActionDispatcher client_action_dispatcher_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_H_
