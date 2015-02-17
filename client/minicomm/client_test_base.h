#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_TEST_BASE_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_TEST_BASE_H_

#include <memory>
#include <string>

#include "gtest/gtest.h"
#include "config.h"

namespace grr {
class ClientTestBase : public ::testing::Test {
 public:
  ClientTestBase();
  ~ClientTestBase();

  // This sets up  config_ with a config file usable for most purposes.
  void SetUpDefaultConfig();
  void SetUp() override { SetUpDefaultConfig(); }

  // Methods to write a config file, providing more control over the resulting
  // configuration. Be sure to call config_.ReadConfig after using.
  void WriteValidConfigFile(bool include_private_key, bool use_writeback);
  void WriteConfigFile(const std::string& data);

  // Retrieve current writeback file.
  std::string ReadWritebackFile();

  // Resets the log capture buffer and begins copying logged messages to it.
  void BeginLogCapture(const std::set<LogLevel>& levels);
  // Stops capturing log messages.
  void EndLogCapture();
  // Check if the buffer contains a log line which ends in string.
  bool CapturedLogContainsSuffix(const std::string& string);

  const std::string tmp_dir_;
  const std::string config_filename_;
  const std::string writeback_filename_;
  ClientConfig config_;

  // A valid CA certificate.
  static const char kCertPEM[];
  // A valid RSA private key.
  static const char kPrivateRSAPEM[];

 private:

  class LogCaptureSink;

  std::unique_ptr<LogCaptureSink> log_capture_sink_;
};

}  // namespace grr
#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CLIENT_TEST_BASE_H_
