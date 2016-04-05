#include "grr/client/minicomm/client_test_base.h"

#include <stdlib.h>
#include <fstream>

#include "grr/client/minicomm/logging_control.h"
#include "grr/client/minicomm/test_util.h"

namespace grr {

ClientTestBase::ClientTestBase()
    : tmp_dir_(testing::MakeTempDir()),
      config_filename_(tmp_dir_ + "/config"),
      writeback_filename_(tmp_dir_ + "/writeback"),
      config_(config_filename_) {}

ClientTestBase::~ClientTestBase() {}

void ClientTestBase::WriteConfigFile(const std::string& data) {
  std::ofstream file;
  file.open(config_filename_);
  file << data;
  file.close();
}

void ClientTestBase::SetUpDefaultConfig() {
  WriteValidConfigFile(false, false);
}

void ClientTestBase::WriteValidConfigFile(bool include_private_key,
                                          bool use_writeback) {
  ClientConfiguration config_proto;
  config_proto.add_control_url("http://localhost:8001/control");
  config_proto.set_ca_cert_pem(kCertPEM);

  config_proto.set_temporary_directory(tmp_dir_);

  if (include_private_key) {
    config_proto.set_client_private_key_pem(kPrivateRSAPEM);
  }
  if (use_writeback) {
    config_proto.set_writeback_filename(writeback_filename_);
  }
  WriteConfigFile(config_proto.DebugString());
}

std::string ClientTestBase::ReadWritebackFile() {
  std::ifstream file;
  file.open(writeback_filename_);
  const std::string r((std::istreambuf_iterator<char>(file)),
                      std::istreambuf_iterator<char>());
  file.close();
  return r;
}

const char ClientTestBase::kCertPEM[] =
    R"(-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----
)";

const char ClientTestBase::kPrivateRSAPEM[] =
    R"(-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAvI1Jn+IoMe02PS20/pry1PcU0Uv57NodJZ70YyQM8sO3SRxW
kxnQX9FZGZ42iURAOdQVuAMfvjIcUa6p++l2T4mBBG/YhmKQF8hoFIse9Kp6WGV8
76o+xoDIUqok36UmtwiRmdPVo/XGek7GdhWE+14wbF57J25AiXokBZfg+57pzucw
s5AZUGRa5f5r+bSyHdu4Jg82/Bd32A26XREo+954N6G19QCYOR4qTNBjt6l98W+s
YGBeQpyr1h5hveeWWgNDKV8+k+72njxktiNy8w/8n7JIMXT2dCNzia5/j3RrX73k
gFU+x5w8g/0QruPvjAJSs1jkxjJIX2TWIPrQMwIDAQABAoIBAQCOp5b8kG841vAi
eWJm/3SaDBaEA6eju6IxxIHCQJRLWChj+DzILs+orwtqhnlcgXbWSc/k2Pg7Pk6O
vkd9gLUymCY05So9AnViiQ21/Uv+cL0ABEjySywTo3vsjy42xwzzjlgaulr5Igp4
nwEodj+WrzyTwSgMPS421WJLmQ1vUQ+1FT3yPU4ljtvoyxNagaVTY9ZbTxtCqcmt
CliP5WgC6vsqcV8VbK5LQT1ycyeNXsxpFwGEUn7FVDmT9XetvN2G3uu+56lRa35Z
ai6baECDspVBvoaSDkKWqUFhZAgnzW8KFOTLpxHFFLESSFRNuSdiTAqIA8C+SPUV
fcSxuLIBAoGBAN9183iDdUt9Lmk3912KOfl9rf4NlOjogH+2un/5OmM6PMNb9ONc
fAMJCMdF0jGKkIC2p1f4VseKYYrMT20r1XV/p4jbVkfTVTBG6ys2GFrO+Rgjx7/9
sciiE87SewY/Cqg48aQ5Iy1nNX+wLg+K1+PRKZODKSsqVuy+bk75PqaxAoGBANgC
Bgrr+muB8MtPfR9CL0010NN14N6MK5lDAhQsLBCjYcdAZClhhffHq5rEp/wl9enG
s5+FQn08eEObx8qBxhJLd04Zuh0zUT8rkvBIAAvFUqdqN/mJUZHqSVgqk1Tn4tRL
iaznZHi8+IH5mB6Ei6XQ4pftx23uFWnYYLVV1+YjAoGBAItOZPIEQeNFruE5WqSd
v3ahuw5eOS7ZgwIbUDjnjla9v5OqiAgVZ9ocj7Rq+paX423acIiO8MqEojp9FCbi
5LfTVQYkdq1gOgNWstTFbHlv/inmZGh0J5kEMYUGAlvqgSJOHZZbaGqtpNRtaMmX
rO8BPgIQCmI2iuob7XieOUiBAoGALz26DpdvbCW+AOkAh16VM8CqTCUCqglj26AB
C2JhvL3Ou6IEhdxTTU545F9QEeBHePpA/IlLclJQRxEBz/Mz23pvvD/6KTq48STZ
fP1yLSDZo82iMkvq8AuaQNMG59HTFPT0RkFRAurpOpvYvgvk8r3NYMbbD9q7CiwN
cns0vZsCgYEApekMPRZw/l9ZC0CRfswb6EpUFjgM6yflPeFsyCNTEGlpQuIdAWCf
I8WVhjQT+yJUAlPJVWmYrXqpFzAD3r20qPg6i2tYsVTYhnr8htEyxibUpoNp2XIl
Ez6jWXu/xkywXaxZ5SqHIGPqvhdG4eOercH6iKOEdmyK0+7AxraXGaQ=
-----END RSA PRIVATE KEY-----
)";

class ClientTestBase::LogCaptureSink : public LogSink {
 public:
  explicit LogCaptureSink(const std::set<LogLevel>& severities)
      : severities_to_log_(severities) {
    LogControl::AddLogSink(this);
  }

  ~LogCaptureSink() { StopLogging(); }

  void StopLogging() {
    std::unique_lock<std::mutex> l(mutex_);
    LogControl::RemoveLogSink(this);
  }

  void Log(LogLevel level, const char* filename, int line,
           const std::string& message) {
    std::unique_lock<std::mutex> l(mutex_);
    if (severities_to_log_.count(level)) {
      messages_.push_back(message);
    }
  }

  bool ContainsMessageWithSuffix(const std::string& suffix) {
    std::unique_lock<std::mutex> l(mutex_);
    for (const auto& m : messages_) {
      if (m.size() >= suffix.size() &&
          m.compare(m.size() - suffix.size(), suffix.size(), suffix) == 0) {
        return true;
      }
    }
    return false;
  }

 private:
  std::mutex mutex_;
  std::vector<std::string> messages_;
  const std::set<LogLevel> severities_to_log_;
};

void ClientTestBase::BeginLogCapture(const std::set<LogLevel>& severities) {
  log_capture_sink_.reset(new LogCaptureSink(severities));
}

void ClientTestBase::EndLogCapture() {
  GOOGLE_CHECK(log_capture_sink_ != nullptr);
  log_capture_sink_->StopLogging();
}

bool ClientTestBase::CapturedLogContainsSuffix(const std::string& message) {
  GOOGLE_CHECK(log_capture_sink_ != nullptr);
  return log_capture_sink_->ContainsMessageWithSuffix(message);
}
}  // namespace grr
