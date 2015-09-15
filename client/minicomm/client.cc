#include "grr/client/minicomm/client.h"

#include <thread>

#include "grr/client/minicomm/base.h"

#include "grr/client/minicomm/client_actions/delete_grr_temp_files.h"
#include "grr/client/minicomm/client_actions/dump_process_memory.h"
#include "grr/client/minicomm/client_actions/enumerate_filesystems.h"
#include "grr/client/minicomm/client_actions/enumerate_interfaces.h"
#include "grr/client/minicomm/client_actions/enumerate_users.h"
#include "grr/client/minicomm/client_actions/find.h"
#include "grr/client/minicomm/client_actions/fingerprint_file.h"
#include "grr/client/minicomm/client_actions/get_client_info.h"
#include "grr/client/minicomm/client_actions/get_configuration.h"
#include "grr/client/minicomm/client_actions/get_install_date.h"
#include "grr/client/minicomm/client_actions/get_library_versions.h"
#include "grr/client/minicomm/client_actions/get_platform_info.h"
#include "grr/client/minicomm/client_actions/grep.h"
#include "grr/client/minicomm/client_actions/list_directory.h"
#include "grr/client/minicomm/client_actions/list_processes.h"
#include "grr/client/minicomm/client_actions/stat_file.h"
#include "grr/client/minicomm/client_actions/transfer_buffer.h"

namespace grr {
Client::Client(const std::string& filename)
    : config_(filename),
      inbox_(5000, 1000000),
      outbox_(5000, 1000000),
      connection_manager_(&config_, &inbox_, &outbox_),
      client_action_dispatcher_(&inbox_, &outbox_, &config_) {
  if (!config_.ReadConfig()) {
    GOOGLE_LOG(FATAL) << "Unable to read config.";
  }
  if (config_.ClientId().empty()) {
    config_.ResetKey();
  }
  GOOGLE_LOG(INFO) << "I am " << config_.ClientId();
}

void Client::StaticInit() {
  GOOGLE_PROTOBUF_VERIFY_VERSION;
  HttpConnectionManager::StaticInit();
}

void Client::Run() {
  client_action_dispatcher_.AddAction("DumpProcessMemory",
                                      new actions::DumpProcessMemory());
  client_action_dispatcher_.AddAction("DeleteGRRTempFiles",
                                      new actions::DeleteGRRTempFiles());
  client_action_dispatcher_.AddAction("EnumerateFilesystems",
                                      new actions::EnumerateFilesystems());
  client_action_dispatcher_.AddAction("EnumerateInterfaces",
                                      new actions::EnumerateInterfaces());
  client_action_dispatcher_.AddAction("EnumerateUsers",
                                      new actions::EnumerateUsers());
  client_action_dispatcher_.AddAction("GetClientInfo",
                                      new actions::GetClientInfo());
  client_action_dispatcher_.AddAction("GetConfiguration",
                                      new actions::GetConfiguration());
  client_action_dispatcher_.AddAction("GetInstallDate",
                                      new actions::GetInstallDate());
  client_action_dispatcher_.AddAction("GetLibraryVersions",
                                      new actions::GetLibraryVersions());
  client_action_dispatcher_.AddAction("GetPlatformInfo",
                                      new actions::GetPlatformInfo());
  client_action_dispatcher_.AddAction("Grep", new actions::Grep());
  client_action_dispatcher_.AddAction("Find", new actions::Find());
  client_action_dispatcher_.AddAction("FingerprintFile",
                                      new actions::FingerprintFile());
  client_action_dispatcher_.AddAction("HashFile",
                                      new actions::FingerprintFile());
  client_action_dispatcher_.AddAction("ListDirectory",
                                      new actions::ListDirectory());
  client_action_dispatcher_.AddAction("ListProcesses",
                                      new actions::ListProcesses());
  client_action_dispatcher_.AddAction("StatFile", new actions::StatFile());
  client_action_dispatcher_.AddAction("HashBuffer",
                                      new actions::TransferBuffer());
  client_action_dispatcher_.AddAction("TransferBuffer",
                                      new actions::TransferBuffer());
  client_action_dispatcher_.StartProcessing();

  std::thread connection_manager_thread(
      [this] { this->connection_manager_.Run(); });

  connection_manager_thread.join();
}
}  // namespace grr
