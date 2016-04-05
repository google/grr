#include "grr/client/minicomm/message_queue.h"

#include <chrono>
#include <memory>
#include <ratio>
#include <string>
#include <thread>

#include "gtest/gtest.h"

namespace grr {

TEST(MessageQueueTest, AddMessageNonBlocking) {
  MessageQueue queue(5, 20000);

  GrrMessage m0;
  m0.set_session_id("SESSION 0");
  m0.set_args(std::string("123457890", 10));
  queue.AddMessage(m0);

  GrrMessage m1;
  m1.set_session_id("SESSION 1");
  m1.set_args(std::string("0987654321", 10));
  queue.AddMessage(m1);

  GrrMessage m2;
  m2.set_session_id("SESSION 2");
  queue.AddMessage(m2);

  EXPECT_EQ(3, queue.current_message_count());
  EXPECT_EQ(20, queue.current_args_size());

  std::vector<GrrMessage> messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(3, messages.size());
  EXPECT_EQ("SESSION 0", messages[0].session_id());
  EXPECT_EQ("SESSION 1", messages[1].session_id());
  EXPECT_EQ("SESSION 2", messages[2].session_id());
}

TEST(MessageQueueTest, AddMessageBlocks) {
  MessageQueue queue(5, 15);

  GrrMessage m0;
  m0.set_session_id("SESSION 0");
  m0.set_args(std::string("123457890", 10));
  queue.AddMessage(m0);

  // Will only fit in the queue when the queue is empty.
  GrrMessage m1;
  m1.set_session_id("SESSION 1");
  m1.set_args(std::string("09876543210987654321", 20));
  std::thread blocked_add([&m1, &queue]() { queue.AddMessage(m1); });

  // Pause so that blocked_add is likely to run if it can.
  std::this_thread::sleep_for(std::chrono::milliseconds(100));
  // Should only get m1 back, because blocked_add should be blocked.
  std::vector<GrrMessage> messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(1, messages.size());
  EXPECT_EQ("SESSION 0", messages[0].session_id());

  // Now blocked_add should run.
  blocked_add.join();
  messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(1, messages.size());
  EXPECT_EQ("SESSION 1", messages[0].session_id());
}

TEST(MessageQueueTest, AddPriorityMessage) {
  MessageQueue queue(5, 15);

  // Overfill the queue:
  GrrMessage m0;
  m0.set_session_id("SESSION 0");
  m0.set_args(std::string("1234578901234567890", 20));
  queue.AddMessage(m0);

  // A priority message should still go in, and go to the front of the queue.
  GrrMessage m1;
  m1.set_session_id("SESSION 1");
  m1.set_args(std::string("0987654321", 10));
  queue.AddPriorityMessage(m1);

  std::vector<GrrMessage> messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(2, messages.size());
  // High priority message should be first.
  EXPECT_EQ("SESSION 1", messages[0].session_id());
  EXPECT_EQ("SESSION 0", messages[1].session_id());
}

TEST(MessageQueueTest, GetMessageBlocking) {
  MessageQueue queue(5, 15);

  // Non-blocking mode should return immediatly, even when the queue is empty.
  std::vector<GrrMessage> messages = queue.GetMessages(5, 20000, false);

  std::thread blocked_get(
      [&messages, &queue]() { messages = queue.GetMessages(2, 20000, true); });
  std::this_thread::sleep_for(std::chrono::milliseconds(100));

  GrrMessage m0;
  m0.set_session_id("SESSION 0");
  m0.set_args(std::string("123457890", 10));
  queue.AddMessage(m0);

  // Now blocked_get should run.
  blocked_get.join();
  ASSERT_EQ(1, messages.size());
  EXPECT_EQ("SESSION 0", messages[0].session_id());
}

TEST(MessageQueueTest, GetMessageSize) {
  MessageQueue queue(100, 10000);
  for (int i = 0; i < 10; i++) {
    GrrMessage m;
    m.set_session_id("SESSION " + std::to_string(i));
    m.set_args(std::string("123457890", 10));
    queue.AddMessage(m);
  }
  std::vector<GrrMessage> messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(5, messages.size());
  EXPECT_EQ("SESSION 0", messages[0].session_id());
  EXPECT_EQ("SESSION 4", messages[4].session_id());
  messages = queue.GetMessages(5, 20000, false);
  ASSERT_EQ(5, messages.size());
  EXPECT_EQ("SESSION 5", messages[0].session_id());
  EXPECT_EQ("SESSION 9", messages[4].session_id());
}
}  // namespace grr
