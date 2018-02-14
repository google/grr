// Copyright 2012 Google Inc
// All Rights Reserved.

#include "grr_response_client/nanny/event_logger.h"

#include "testing/base/public/gmock.h"
#include "testing/base/public/gunit.h"

using ::testing::_;
using ::testing::Return;

namespace grr {

class MockLogger : public EventLogger {
 public:
  MOCK_METHOD0(GetCurrentTime, time_t());
  MOCK_METHOD1(WriteLog, void(std::string));
};


class LoggerTest : public ::testing::Test {};

TEST_F(LoggerTest, WritesMessageToLog) {
  // This test verifies that Logger writes a message to the Log source.
  MockLogger logger;

  EXPECT_CALL(logger, WriteLog(_))
      .Times(1);

  logger.Log("Test");
}

TEST_F(LoggerTest, RepeatedMessagesAreNotSuppresed) {
  // This test verifies that Logger does not suppress repeated messages after
  // the time period.
  MockLogger logger;

  // Set the logger suppression time.
  logger.set_message_suppression_time(10);

  EXPECT_CALL(logger, GetCurrentTime())
      .Times(3)
      .WillOnce(Return(10))
      .WillOnce(Return(25))
      .WillOnce(Return(36));

  // We still expect two messages to be written.
  EXPECT_CALL(logger, WriteLog(_))
      .Times(3);

  // Log 3 times in rapid succession
  for (int i = 0; i < 3; i++) {
    logger.Log("Test");
  }
}

TEST_F(LoggerTest, RepeatedMessagesAreSuppressed) {
  // This test verifies that Logger suppresses repeated messages within the time
  // period.
  MockLogger logger;

  // Set the logger suppression time.
  logger.set_message_suppression_time(60);

  EXPECT_CALL(logger, GetCurrentTime())
      .WillOnce(Return(1))
      .WillOnce(Return(2))
      .WillOnce(Return(3));

  // We still expect only a single message to be written.
  EXPECT_CALL(logger, WriteLog(_))
      .Times(1);

  // Log 3 times in rapid succession
  for (int i = 0; i < 3; i++) {
    logger.Log("Test");
  }
}

}  // namespace grr
