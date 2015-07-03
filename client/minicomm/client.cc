#include "grr/client/minicomm/client.h"

#include <thread>

#include "grr/client/minicomm/base.h"

#include "grr/client/minicomm/client_actions/enumerate_filesystems.h"
#include "grr/client/minicomm/client_actions/enumerate_interfaces.h"
#include "grr/client/minicomm/client_actions/get_platform_info.h"


namespace grr {
Client::Client(const std::string& filename)
    : config_(filename),
      inbox_(5000, 1000000),
      outbox_(5000, 1000000),
      connection_manager_(&config_, &inbox_, &outbox_),
      client_action_dispatcher_(&inbox_, &outbox_) {
  if (!config_.ReadConfig()) {
    GOOGLE_LOG(FATAL) << "Unable to read config.";
  }
  if (config_.ClientId().empty()) {
    config_.ResetKey();
  }
  GOOGLE_LOG(INFO) << "I am " << config_.ClientId();
}

void Client::StaticInit() {
  HttpConnectionManager::StaticInit();
}

void Client::Run() {
  client_action_dispatcher_.AddAction(new EnumerateFilesystems());
  client_action_dispatcher_.AddAction(new EnumerateInterfaces());
  client_action_dispatcher_.AddAction(new GetPlatformInfo());
  client_action_dispatcher_.StartProcessing();

  std::thread connection_manager_thread(
      [this] { this->connection_manager_.Run(); });

  connection_manager_thread.join();
}
}  // namespace grr
