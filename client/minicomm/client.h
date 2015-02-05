#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_H_

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
  Client(const string& filename);
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

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_H_
