#include "config.h"

#include <stddef.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <io.h>
#else
#include <fcntl.h>
#endif

#include "grr/client/minicomm/config.pb.h"
#include "grr/client/minicomm/util.h"
#include "google/protobuf/io/zero_copy_stream_impl.h"
#include "google/protobuf/text_format.h"

namespace grr {
ClientConfig::ClientConfig(const std::string& configuration_file)
    : configuration_filename_(configuration_file) {}

bool ClientConfig::ReadConfig() {
  ClientConfiguration proto;
  if (!MergeConfigFile(configuration_filename_, &proto)) {
    GOOGLE_LOG(ERROR) << "Unable to read config:" << configuration_filename_;
    return false;
  }
  std::unique_lock<std::mutex> l(lock_);

  writeback_filename_ = proto.writeback_filename();
  if (!writeback_filename_.empty()) {
    if (!MergeConfigFile(writeback_filename_, &proto)) {
      GOOGLE_LOG(ERROR) << "Unable to read writeback:" << writeback_filename_;
    }
  } else {
    GOOGLE_LOG(WARNING) << "No writeback filename. Writeback disabled.";
  }

  subprocess_config_ = proto.subprocess_config();
  last_server_cert_serial_number_ = proto.last_server_cert_serial_number();

  control_urls_ = proto.control_url();
  proxy_servers_ = proto.proxy_server();

  key_.FromPEM(proto.client_private_key_pem());
  ca_cert_.FromPEM(proto.ca_cert_pem());
  temporary_directory_ = proto.temporary_directory();

  client_id_ = MakeClientId();
  if (!control_urls_.size()) {
    GOOGLE_LOG(ERROR) << "No control URLs.";
    return false;
  }
  if (ca_cert_.get() == NULL) {
    GOOGLE_LOG(ERROR) << "Missing or bad ca cert.";
    return false;
  }
  return true;
}

bool ClientConfig::CheckUpdateServerSerial(int new_serial) {
  std::unique_lock<std::mutex> l(lock_);
  if (new_serial < last_server_cert_serial_number_) {
    return false;
  }
  if (new_serial > last_server_cert_serial_number_) {
    last_server_cert_serial_number_ = new_serial;
    return WriteBackConfig();
  }
  return true;
}

bool ClientConfig::ResetKey() {
  std::unique_lock<std::mutex> l(lock_);
  if (!key_.Generate()) {
    return false;
  }
  client_id_ = MakeClientId();
  return WriteBackConfig();
}

std::vector<std::string> ClientConfig::ControlUrls() const {
  std::unique_lock<std::mutex> l(lock_);
  return std::vector<std::string>(control_urls_.begin(), control_urls_.end());
}

std::vector<std::string> ClientConfig::ProxyServers() const {
  std::unique_lock<std::mutex> l(lock_);
  return std::vector<std::string>(proxy_servers_.begin(), proxy_servers_.end());
}

ClientConfiguration::SubprocessConfig ClientConfig::SubprocessConfig() const {
  std::unique_lock<std::mutex> l(lock_);
  return subprocess_config_;
}

bool ClientConfig::WriteBackConfig() {
  if (writeback_filename_.empty()) {
    return true;
  }
  int fd = open(writeback_filename_.c_str(), O_WRONLY | O_TRUNC | O_CREAT,
                S_IWUSR | S_IRUSR);
  if (fd < 0) {
    GOOGLE_LOG(ERROR) << "Unable to open writeback: " << writeback_filename_;
    return false;
  }
  // Re-read the original configuration file, so we can tell what has changed.
  ClientConfiguration base_config;
  if (!MergeConfigFile(configuration_filename_, &base_config)) {
    GOOGLE_LOG(ERROR) << "Unable to read config: " << configuration_filename_;
  }
  // Currently only 2 fields can be changed through the config interface.
  ClientConfiguration proto;
  if (base_config.last_server_cert_serial_number() !=
      last_server_cert_serial_number_) {
    proto.set_last_server_cert_serial_number(last_server_cert_serial_number_);
  }
  std::string key_pem = key_.ToStringPEM();
  if (base_config.client_private_key_pem() != key_pem) {
    proto.set_client_private_key_pem(key_pem);
  }

  google::protobuf::io::FileOutputStream output(fd);
  bool result = google::protobuf::TextFormat::Print(proto, &output);
  output.Close();
  return result;
}

std::string ClientConfig::MakeClientId() {
  if (!key_.get()) {
    return "";
  }
  return "C." + BytesToHex(Digest::Hash(Digest::Type::SHA256, key_.PublicKeyN())
                               .substr(0, 8));
}

bool ClientConfig::MergeConfigFile(const std::string& config_file,
                                   ClientConfiguration* config) {
  int fd = open(config_file.c_str(), O_RDONLY);
  if (fd < 0) {
    GOOGLE_LOG(ERROR) << "Failed to open:" << config_file;
    return false;
  }

  google::protobuf::io::FileInputStream input(fd);
  if (!google::protobuf::TextFormat::Merge(&input, config)) {
    GOOGLE_LOG(ERROR) << "Failed to parse:" << config_file;
    input.Close();
    return false;
  }
  input.Close();
  return true;
}
}  // namespace grr
