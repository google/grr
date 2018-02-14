// Copyright 2012 Google Inc
// All Rights Reserved.

#include "grr_response_client/nanny/child_controller.h"

#include "testing/base/public/gmock.h"
#include "testing/base/public/gunit.h"

using ::testing::_;
using ::testing::Assign;
using ::testing::AtLeast;
using ::testing::Return;
using ::testing::ReturnPointee;
using ::testing::Mock;

namespace grr {

class MockChildProcess : public ChildProcess {
 public:
  MOCK_METHOD0(CreateChildProcess, bool());
  MOCK_METHOD0(GetHeartbeat, time_t());
  MOCK_METHOD0(ClearHeartbeat, void());
  MOCK_METHOD1(SetHeartbeat, void(unsigned int));
  MOCK_METHOD0(Heartbeat, void());
  MOCK_METHOD1(KillChild, void(const std::string &msg));
  MOCK_METHOD0(GetCurrentTime, time_t());
  MOCK_METHOD0(IsAlive, bool());
  MOCK_METHOD0(Started, bool());
  MOCK_METHOD0(GetMemoryUsage, size_t());
  MOCK_METHOD1(SetNannyMessage, void(const std::string &msg));
  MOCK_METHOD1(SetNannyStatus, void(const std::string &msg));
  MOCK_METHOD1(SetPendingNannyMessage, void(const std::string &msg));
  MOCK_METHOD1(ChildSleep, void(unsigned int));
};

class ChildTest : public ::testing::Test {};

const struct ControllerConfig kConfig = {
  60,   // resurrection_period
  30,   // unresponsive_kill_period
  300,  // unresponsive_grace_period
  60,   // event_log_message_suppression
};


TEST_F(ChildTest, StartsChildAtStartUp) {
  // This test verifies that Child process is started upon construction.
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);

  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, GetCurrentTime())
      .WillOnce(Return(1000));

  EXPECT_CALL(child, GetHeartbeat())
      .WillOnce(Return(100));

  child_controller.Run();

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

ACTION_P(SetAndReturn, p) {
  *p = true;
  return true;
};


TEST_F(ChildTest, KillUnresponsiveChild) {
  // This test verifies that unresponsive children are killed and not restarted
  // until the resurrection_period. See comments atop child_controller.h.

  int current_epoch;
  bool alive = false;
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  ON_CALL(child, IsAlive())
      .WillByDefault(ReturnPointee(&alive));

  ON_CALL(child, Started())
      .WillByDefault(ReturnPointee(&alive));

  ON_CALL(child, CreateChildProcess())
      .WillByDefault(SetAndReturn(&alive));

  ON_CALL(child, KillChild(_))
      .WillByDefault(Assign(&alive, false));

  ON_CALL(child, GetHeartbeat())
      .WillByDefault(Return(10));

  // Run for 20 seconds - child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild(_))
      .Times(0);

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020; ++current_epoch) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));

  // We now expect the child to be killed at least once and not restarted.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(0);

  EXPECT_CALL(child, KillChild(_))
      .Times(AtLeast(1));

  // Scan the time line.
  for (; current_epoch < 1040; ++current_epoch) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child_controller));

  // And now we expect the child to be started again.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild(_))
      .Times(0);

  // Scan the time line - After 60 seconds we should start the child.
  for (current_epoch = 1040; current_epoch < 1100; current_epoch++) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

TEST_F(ChildTest, SteadyState) {
  // This test verifies that in the steady state we do not kill the children.
  int current_epoch;
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);
  std::string msg;

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  // Run for 20 seconds - child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild(msg))
      .Times(0);

  ON_CALL(child, GetHeartbeat())
      .WillByDefault(Return(100));

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020; current_epoch++) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));

  // Now the child heartbeats as normal.
  ON_CALL(child, GetHeartbeat())
      .WillByDefault(ReturnPointee(&current_epoch));

  EXPECT_CALL(child, CreateChildProcess())
      .Times(0);

  EXPECT_CALL(child, KillChild(msg))
      .Times(0);

  // Run for 200 more seconds - We should not kill the child.
  for (; current_epoch < 1220; current_epoch += 10) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

TEST_F(ChildTest, TestSuspending) {
  // This test verifies that when the machine suspends, the client does not
  // get killed.
  int current_epoch, current_hb = 1;
  time_t sleep_time = 0;
  bool alive = false;
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);
  std::string msg;

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  ON_CALL(child, GetHeartbeat())
      .WillByDefault(ReturnPointee(&current_hb));

  ON_CALL(child, IsAlive())
      .WillByDefault(ReturnPointee(&alive));

  ON_CALL(child, CreateChildProcess())
      .WillByDefault(SetAndReturn(&alive));

  // Run for 20 seconds - child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild(msg))
      .Times(0);

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020;
       current_epoch += sleep_time) {
    sleep_time = child_controller.Run();
  }

  // Scan the time line.
  for (; current_epoch < 2000; current_epoch += sleep_time) {
    // The child heartbeats only every 10 seconds.
    current_hb = (current_epoch / 10) * 10;
    sleep_time = child_controller.Run();
  }

  // The machine suspends.
  current_epoch = 100000;

  // Scan the time line, child should not be killed.
  for (; current_epoch < 102000; current_epoch += sleep_time) {
    if ((current_epoch / 10) * 10 >= 100000) {
      current_hb = (current_epoch / 10) * 10;
    }
    sleep_time = child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

TEST_F(ChildTest, TestSuspendingWhenNannyWakesUpEarlier) {
  // This test verifies that when the nanny wakes up from a resume before the
  // client is ready, it waits and doesn't kill it right away.
  int current_epoch, current_hb = 0;
  int * p_epoch = &current_epoch;
  time_t sleep_time = 0;
  bool alive = false;
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);
  std::string msg;
  bool started = false;

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  ON_CALL(child, GetHeartbeat())
      .WillByDefault(ReturnPointee(&current_hb));

  ON_CALL(child, IsAlive())
      .WillByDefault(ReturnPointee(&alive));

  ON_CALL(child, Started())
      .WillByDefault(ReturnPointee(&started));

  ON_CALL(child, CreateChildProcess())
      .WillByDefault(DoAll(Assign(&started, true), SetAndReturn(&alive)));

  // Child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild(msg))
      .Times(0);

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020;
       current_epoch += sleep_time) {
    sleep_time = child_controller.Run();
  }

  for (current_epoch = 1020; current_epoch < 1200;
       current_epoch += sleep_time) {
    // The child heartbeats only every 10 seconds.
    current_hb = (current_epoch / 10) * 10;
    sleep_time = child_controller.Run();
  }

  // The machine suspends.
  current_epoch = 100000;

  // While the nanny sleeps there should be a heartbeat.
  ON_CALL(child, ChildSleep(2000))
      .WillByDefault(Assign(&current_hb, *p_epoch));

  // Scan the time line, child should not be killed.
  for (; current_epoch < 102000; current_epoch += sleep_time) {
    // Add a 5 second delay to the heartbeat.
    if (((current_epoch) / 10) * 10 >= 100000 + 5) {
      current_hb = (current_epoch / 10) * 10;
    }
    sleep_time = child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

}  // namespace grr.
