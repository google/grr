#include "subprocess_delegator.h"

#include <chrono>
#include <ratio>
#include <string>
#include <vector>

#include "google/protobuf/stubs/common.h"
#include "client_test_base.h"
#include "config.h"
#include "config.pb.h"
#include "message_queue.h"
#include "google/protobuf/repeated_field.h"
#include "gtest/gtest.h"

namespace grr {

class SubprocessDelegatorTest : public ClientTestBase {
 protected:
  SubprocessDelegatorTest() :
      mock_delegate_(FLAGS_test_srcdir +
      "/google3/"
      "mock_delegate.sh"),
      inbox_(100, 100000),
      outbox_(100, 100000) {}

  void SetConfiguration(const string& filename,
                        const vector<string>& argv,
                        const vector<string>& env) {
    ClientConfiguration config_proto;
    config_proto.add_control_url("http://localhost:8001/control");
    config_proto.set_ca_cert_pem(kCertPEM);

    ClientConfiguration::SubprocessConfig* subprocess_config =
        config_proto.mutable_subprocess_config();
    subprocess_config->set_filename(filename);
    *subprocess_config->mutable_argv() = proto2::RepeatedPtrField<string>(
        argv.begin(), argv.end());
    *subprocess_config->mutable_env() = proto2::RepeatedPtrField<string>(
        env.begin(), env.end());

    WriteConfigFile(config_proto.DebugString());

    CHECK(config_.ReadConfig());
  }

  void StartDelegator() {
    delegator_.reset(new SubprocessDelegator(&config_,
                                             &inbox_,
                                             &outbox_));
  }

  const string mock_delegate_;

  MessageQueue inbox_;
  MessageQueue outbox_;
  std::unique_ptr<SubprocessDelegator> delegator_;
};

TEST_F(SubprocessDelegatorTest, NewDelete) {
  SetConfiguration("/bad/filename/", std::vector<string>(),
                   std::vector<string>());
  StartDelegator();
  std::this_thread::sleep_for(std::chrono::seconds(2));
}

TEST_F(SubprocessDelegatorTest, BadConfig) {
  SetConfiguration("/bad/filename/", std::vector<string>(),
                   std::vector<string>());
  StartDelegator();
  BeginLogCapture({ERROR});
  inbox_.AddMessage(MessageQueue::Message());
  std::this_thread::sleep_for(std::chrono::seconds(2));
  // With a bad filename, execve should fail, and we should be told.
  EXPECT_TRUE(
      CapturedLogContainsSuffix("From subprocess: Child Unable to execve!"));
}
TEST_F(SubprocessDelegatorTest, SubprocessError) {
  vector<string> argv = {"startup-error"};
  SetConfiguration(mock_delegate_, argv, std::vector<string>());
  StartDelegator();
  BeginLogCapture({ERROR});
  inbox_.AddMessage(MessageQueue::Message());
  std::this_thread::sleep_for(std::chrono::seconds(2));
  // We should get a startup error message from the subprocess.
  EXPECT_TRUE(CapturedLogContainsSuffix("From subprocess: Subprocess Error"));
}

TEST_F(SubprocessDelegatorTest, SubprocessGarbage) {
  vector<string> argv = {"garbage-out"};
  SetConfiguration(mock_delegate_, argv, std::vector<string>());
  StartDelegator();
  BeginLogCapture({ERROR});
  inbox_.AddMessage(MessageQueue::Message());
  std::this_thread::sleep_for(std::chrono::seconds(5));
  // We should not be able to process the garbage, and so should reset the
  // subprocess.
  EXPECT_TRUE(
      CapturedLogContainsSuffix("Read bad size, resetting the subprocess."));
}

TEST_F(SubprocessDelegatorTest, SubprocessSlow) {
  vector<string> argv = {"sleepy"};
  SetConfiguration(mock_delegate_, argv, std::vector<string>());
  StartDelegator();
  std::this_thread::sleep_for(std::chrono::seconds(5));
}

TEST_F(SubprocessDelegatorTest, SimpleLoopback) {
  vector<string> argv = {"loop-back"};
  SetConfiguration(mock_delegate_, argv, std::vector<string>());
  StartDelegator();
  MessageQueue::Message message;
  message.set_session_id("SESSION_ID1");
  message.set_args("ASDFASDFASDF");
  inbox_.AddMessage(message);
  const vector<MessageQueue::Message> result =
      outbox_.GetMessages(5, 100000, true);
  ASSERT_EQ(1, result.size());
  EXPECT_EQ(result[0].session_id(), message.session_id());
  EXPECT_EQ(result[0].args(), message.args());
}
}  // namespace grr
