#include "grr/client/minicomm/comms_utils.h"

#include <fstream>

#include "grr/client/minicomm/client_test_base.h"
#include "gtest/gtest.h"

namespace grr {

class MessageBuilderTest : public ClientTestBase {};

TEST_F(MessageBuilderTest, InitiateEnrollmentWithoutKey) {
  MessageQueue output(5, 1024);

  ASSERT_TRUE(config_.ReadConfig());
  ASSERT_TRUE(config_.key().get() == nullptr);

  MessageBuilder::InitiateEnrollment(&config_, &output);

  EXPECT_TRUE(config_.key().get() != nullptr);
}

TEST_F(MessageBuilderTest, InitiateEnrollment) {
  MessageQueue output(5, 1024);

  WriteValidConfigFile(true, false);
  ASSERT_TRUE(config_.ReadConfig());

  MessageBuilder::InitiateEnrollment(&config_, &output);

  EXPECT_EQ(config_.key().ToStringPEM(), kPrivateRSAPEM);
  EXPECT_EQ(output.current_message_count(), 1);

  auto m = output.GetMessages(1000, 1024, true);

  ASSERT_EQ(m.size(), 1);

  EXPECT_EQ(m[0].session_id(), "aff4:/flows/CA:Enrol");
  EXPECT_EQ(m[0].args_rdf_name(), "Certificate");

  ::Certificate cert_pb;

  ASSERT_TRUE(cert_pb.ParseFromString(m[0].args()));

  EXPECT_EQ(cert_pb.type(), ::Certificate::CSR);
  EXPECT_FALSE(cert_pb.pem().empty());
}


class SecureSessionTest : public ::testing::Test {};

TEST_F(SecureSessionTest, EncodeDecodeMessage) {
  const std::string client_id = "grr";
  RSAKey server_key, client_key;
  int64 nonce = 4;

  server_key.Generate();
  client_key.Generate();

  std::unique_ptr<Certificate> server_cert(new Certificate(server_key));
  std::unique_ptr<Certificate> client_cert(new Certificate(client_key));

  auto session_server =
      SecureSession(client_id, &server_key, std::move(client_cert));
  auto session_client =
      SecureSession(client_id, &client_key, std::move(server_cert));

  // client -> server
  std::vector<GrrMessage> messages_in;
  auto encoded = session_client.EncodeMessages(messages_in, nonce);
  std::vector<GrrMessage> messages_out;
  EXPECT_TRUE(session_server.DecodeMessages(encoded, &messages_out, nonce));
  EXPECT_TRUE(messages_out.empty());

  GrrMessage message;
  std::string plaintext = "Hello encryption!";
  message.set_session_id(plaintext);
  messages_in.push_back(message);
  encoded = session_client.EncodeMessages(messages_in, nonce);
  EXPECT_TRUE(session_server.DecodeMessages(encoded, &messages_out, nonce));
  ASSERT_EQ(messages_out.size(), 1);
  EXPECT_EQ(messages_out[0].session_id(), plaintext);
}

}  // namespace grr
