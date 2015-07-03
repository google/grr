#include "grr/client/minicomm/config.h"

#include <fstream>

#include "grr/client/minicomm/client_test_base.h"
#include "google/protobuf/text_format.h"
#include "gtest/gtest.h"

namespace grr {

class ConfigTest : public grr::ClientTestBase {};

TEST_F(ConfigTest, BadConfig) {
  WriteConfigFile("A bad config file::");
  EXPECT_FALSE(config_.ReadConfig());
}

TEST_F(ConfigTest, GoodConfig) {
  WriteValidConfigFile(false, true);
  EXPECT_TRUE(config_.ReadConfig());
}

TEST_F(ConfigTest, NoPrivateKey) {
  WriteValidConfigFile(false, true);
  ASSERT_TRUE(config_.ReadConfig());

  EXPECT_TRUE(config_.key().get() == nullptr);
}

TEST_F(ConfigTest, Writeback) {
  WriteValidConfigFile(false, true);
  ASSERT_TRUE(config_.ReadConfig());
  ClientConfiguration config_proto;

  config_.ResetKey();
  const std::string client_id = config_.ClientId();
  EXPECT_FALSE(client_id.empty());
  ASSERT_TRUE(google::protobuf::TextFormat::ParseFromString(ReadWritebackFile(),
                                                            &config_proto));
  EXPECT_FALSE(config_proto.client_private_key_pem().empty());
  EXPECT_FALSE(config_proto.has_last_server_cert_serial_number());

  EXPECT_TRUE(config_.CheckUpdateServerSerial(100));
  EXPECT_TRUE(config_.CheckUpdateServerSerial(200));
  EXPECT_FALSE(config_.CheckUpdateServerSerial(150));
  EXPECT_TRUE(config_.CheckUpdateServerSerial(200));

  ASSERT_TRUE(google::protobuf::TextFormat::ParseFromString(ReadWritebackFile(),
                                                            &config_proto));
  EXPECT_EQ(200, config_proto.last_server_cert_serial_number());

  // Verify that a new config will have the same client_id.
  ClientConfig new_config(config_filename_);
  ASSERT_TRUE(new_config.ReadConfig());
  EXPECT_EQ(client_id, new_config.ClientId());
}
}  // namespace grr
