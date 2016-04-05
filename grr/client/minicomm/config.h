#ifndef GRR_CLIENT_MINICOMM_CONFIG_H_
#define GRR_CLIENT_MINICOMM_CONFIG_H_

#include <mutex>
#include <string>
#include <vector>

#include "grr/client/minicomm/config.pb.h"
#include "grr/client/minicomm/crypto.h"
#include "google/protobuf/repeated_field.h"

// Represents the configuration of a client. Thread safe.
namespace grr {
class ClientConfig {
 public:
  // Create a ClientConfig read from the provided filename.
  explicit ClientConfig(const std::string& filename);

  // Attempt to initialize/update ClientConfig from the filesystem. Returns true
  // on success.
  bool ReadConfig();

  // void OverwriteConfig(const ClientConfig& config);

  // Check if new_serial is an acceptable serial number. If the new number is
  // acceptable, returns true and updates the last seen serial number.
  bool CheckUpdateServerSerial(int new_serial);

  // Regenerate our private key.
  bool ResetKey();

  // A client id based on our rsa key. Returns the empty string if we do not
  // have a private rsa key.
  std::string ClientId() const {
    std::unique_lock<std::mutex> l(lock_);
    return client_id_;
  }

  // Our private rsa key, used to identify the client.
  RSAKey key() const {
    std::unique_lock<std::mutex> l(lock_);
    return key_;
  }

  // The certificate used to authenticate servers - the server must present a
  // certificate signed with this key.
  Certificate ca_cert() {
    std::unique_lock<std::mutex> l(lock_);
    return ca_cert_;
  }

  // Directory in which temporary files will be created and deleted.
  std::string TemporaryDirectory() const {
    std::unique_lock<std::mutex> l(lock_);
    return temporary_directory_;
  }

  std::vector<std::string> ControlUrls() const;
  std::vector<std::string> ProxyServers() const;

  ClientConfiguration::SubprocessConfig SubprocessConfig() const;

 private:
  // Attempt to save the current ClientConfig to the filesystem.
  bool WriteBackConfig();

  std::string MakeClientId();

  // Read the file named config_file and merge its content into *config_proto.
  // return true on success.
  static bool MergeConfigFile(const std::string& config_file,
                              ClientConfiguration* config_proto);

  const std::string configuration_filename_;
  std::string writeback_filename_;
  std::string client_id_;

  int last_server_cert_serial_number_;

  google::protobuf::RepeatedPtrField<std::string> control_urls_;
  google::protobuf::RepeatedPtrField<std::string> proxy_servers_;

  ClientConfiguration::SubprocessConfig subprocess_config_;
  std::string temporary_directory_;

  RSAKey key_;
  Certificate ca_cert_;

  mutable std::mutex lock_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CONFIG_H_
