// Copyright 2012 Google Inc
// All Rights Reserved.

#include "grr/client/nanny/child_controller.h"

#include "testing/base/public/gmock.h"
#include "testing/base/public/gunit.h"

using ::testing::_;
using ::testing::AtLeast;
using ::testing::Return;
using ::testing::ReturnPointee;
using ::testing::Mock;

namespace grr {

class MockChildProcess : public ChildProcess {
 public:
  MOCK_METHOD0(CreateChildProcess, bool());
  MOCK_METHOD0(GetHeartBeat, time_t());
  MOCK_METHOD0(KillChild, void());
  MOCK_METHOD0(GetCurrentTime, time_t());
};

class ChildTest : public ::testing::Test {};

const struct ControllerConfig kConfig = {
  60,  // resurrection_period
  30,  // unresponsive_kill_period
  60,  // event_log_message_suppression
};


TEST_F(ChildTest, StartsChildAtStartUp) {
  // This test verifies that Child process is started upon construction.
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);

  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, GetCurrentTime())
      .WillOnce(Return(1000));

  child_controller.Run();

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

TEST_F(ChildTest, KillUnresponsiveChild) {
  // This test verifies that unresponsive children are killed and not restarted
  // until the resurrection_period. See comments atop child_controller.h.

  int current_epoch;
  MockChildProcess child;
  ChildController child_controller(kConfig, &child);

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  // Run for 20 seconds - child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild())
      .Times(0);

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020; ++current_epoch) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));

  // We now expect the child to be killed at least once and not restarted.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(0);

  // It is ok to call KillChild on an already dead child.
  EXPECT_CALL(child, KillChild())
      .Times(AtLeast(1));

  // Scan the time line.
  for (; current_epoch < 1040; ++current_epoch) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child_controller));

  // And now we expect the child to be started again.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild())
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

  ON_CALL(child, GetCurrentTime())
      .WillByDefault(ReturnPointee(&current_epoch));

  // Run for 20 seconds - child should start and not be killed.
  EXPECT_CALL(child, CreateChildProcess())
      .Times(1);

  EXPECT_CALL(child, KillChild())
      .Times(0);

  // Scan the time line.
  for (current_epoch = 1000; current_epoch < 1020; current_epoch++) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));

  // Now the child heartbeats as normal.
  ON_CALL(child, GetHeartBeat())
      .WillByDefault(ReturnPointee(&current_epoch));

  EXPECT_CALL(child, CreateChildProcess())
      .Times(0);

  EXPECT_CALL(child, KillChild())
      .Times(0);

  // Run for 200 more seconds - We should not kill the child.
  for (; current_epoch < 1220; current_epoch += 10) {
    child_controller.Run();
  }

  ASSERT_TRUE(Mock::VerifyAndClearExpectations(&child));
}

}  // namespace grr.
