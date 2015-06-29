#include "grr/client/minicomm/client.h"

#include <thread>

#include "base.h"

namespace grr {
Client::Client(const std::string& filename)
    : config_(filename),
      inbox_(5000, 1000000),
      outbox_(5000, 1000000),
      connection_manager_(&config_, &inbox_, &outbox_),
      subprocess_delegator_(&config_, &inbox_, &outbox_) {
  if (!config_.ReadConfig()) {
    GOOGLE_LOG(FATAL) << "Unable to read config.";
  }
  if (config_.ClientId().empty()) {
    config_.ResetKey();
  }
}
void Client::StaticInit() { HttpConnectionManager::StaticInit(); }

void Client::Run() {
  std::thread connection_manager_thread(
      [this] { this->connection_manager_.Run(); });

  connection_manager_thread.join();
}
}  // namespace grr
