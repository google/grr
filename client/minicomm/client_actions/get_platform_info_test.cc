#include "grr/client/minicomm/client_actions/get_platform_info.h"

#include "gtest/gtest.h"

#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/message_queue.h"
#include "grr/proto/jobs.pb.h"

namespace grr {

TEST(GetPlatformInfoTest, SimpleTest) {
  GrrMessage message;
  MessageQueue queue(5, 20000);
  ActionContext context(message, &queue, nullptr);

  actions::GetPlatformInfo action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(5, 20000, true);
  ASSERT_EQ(1, r.size());
  EXPECT_EQ("Uname", r[0].args_rdf_name());
  Uname response;
  ASSERT_TRUE(response.ParseFromString(r[0].args()));
  // Most of the fields with vary with the machine running the test, but
  // since this is currently just a Linux client, we can at least check that.
  EXPECT_EQ(response.system(), "Linux");
}

}  // namespace grr
