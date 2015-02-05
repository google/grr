#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CONFIG_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CONFIG_H_

#include <mutex>
#include <string>
#include <vector>

#include "config.pb.h"
#include "crypto.h"
#include "google/proto/repeated_field.h"

// Represents the configuration of a client. Thread safe.
namespace grr {
class ClientConfig {
 public:
  // Create a ClientConfig read from the provided filename.
  explicit ClientConfig(const string& filename);

  // Attempt to initialize/update ClientConfig from the filesystem. Returns true
  // on success.
  bool ReadConfig();

  //void OverwriteConfig(const ClientConfig& config);

  // Check if new_serial is an acceptable serial number. If the new number is
  // acceptable, returns true and updates the last seen serial number.
  bool CheckUpdateServerSerial(int new_serial);

  // Regenerate our private key.
  bool ResetKey();

  // A client id based on our rsa key. Returns the empty string if we do not
  // have a private rsa key.
  string ClientId() const {
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

  vector<string> ControlUrls() const;
  vector<string> ProxyServers() const;

  ClientConfiguration::SubprocessConfig SubprocessConfig() const;
 private:
  // Attempt to save the current ClientConfig to the filesystem.
  bool WriteBackConfig();

  string MakeClientId();

  // Read the file named config_file and merge its content into *config_proto.
  // return true on success.
  static bool MergeConfigFile(const string& config_file,
                              ClientConfiguration* config_proto);

  const string configuration_filename_;
  string writeback_filename_;
  string client_id_;

  int last_server_cert_serial_number_;

  proto2::RepeatedPtrField<string> control_urls_;
  proto2::RepeatedPtrField<string> proxy_servers_;

  ClientConfiguration::SubprocessConfig subprocess_config_;

  RSAKey key_;
  Certificate ca_cert_;

  mutable std::mutex lock_;
};

}  // namespace grr

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CONFIG_H_
