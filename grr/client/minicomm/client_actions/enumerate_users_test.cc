#include "grr/client/minicomm/client_actions/enumerate_users.h"

#include "gtest/gtest.h"

#include "grr/proto/knowledge_base.pb.h"
#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/message_queue.h"
#include "grr/proto/jobs.pb.h"

namespace grr {

TEST(EnumerateUsersTest, SimpleTest) {
  GrrMessage message;
  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  actions::EnumerateUsers action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(10, 20000, true);
  for (const auto& m : r) {
    User u;
    ASSERT_TRUE(u.ParseFromString(m.args()));
    GOOGLE_LOG(INFO) << u.DebugString();
  }
}
}  // namespace grr
