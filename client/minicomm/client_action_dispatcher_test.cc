#include "grr/client/minicomm/client_action_dispatcher.h"

#include <chrono>
#include <ratio>

#include "gtest/gtest.h"
#include "google/protobuf/text_format.h"
#include "grr/client/minicomm/message_queue.h"
#include "grr/client/minicomm/test_util.h"

namespace grr {
namespace testing {
std::vector<GrrMessage> GetMessagesExact(int message_count,
                                         MessageQueue* queue) {
  std::vector<GrrMessage> r;
  r.reserve(message_count);
  while (r.size() < message_count) {
    auto results = queue->GetMessages(message_count - r.size(), 100000, true);
    for (auto& result : results) {
      r.insert(r.end(), std::move(result));
    }
  }
  return r;
}
}  // namespace testing

// A fast action which sends PathSpec args back.
class FastAction : public ClientAction {
  void ProcessRequest(ActionContext* context) override {
    PathSpec spec;
    context->PopulateArgs(&spec);
    context->SendResponse(spec, GrrMessage::MESSAGE);
  }
};

// A slow action which sends back an error message.
class SlowAction : public ClientAction {
  void ProcessRequest(ActionContext* context) override {
    std::this_thread::sleep_for(std::chrono::seconds(1));
    context->SetError("Timeout copying path.");
  }
};

TEST(ClientActionDispatcherTest, SimpleTest) {
  MessageQueue inbox(10, 100000);
  MessageQueue outbox(10, 100000);

  ClientActionDispatcher dispatcher(&inbox, &outbox, nullptr);
  dispatcher.AddAction("FastAction", new FastAction());
  dispatcher.AddAction("SlowAction", new SlowAction());
  dispatcher.StartProcessing();

  GrrMessage request_1;
  ASSERT_TRUE(google::protobuf::TextFormat::ParseFromString(
      "request_id: 1 name: 'SlowAction'", &request_1));

  PathSpec path_spec;
  path_spec.set_pathtype(PathSpec::OS);
  path_spec.set_path("/etc/passwd");
  GrrMessage request_2;
  ASSERT_TRUE(google::protobuf::TextFormat::ParseFromString(
      "request_id: 2 name: 'FastAction' args_rdf_name: 'PathSpec'",
      &request_2));
  request_2.set_args(path_spec.SerializeAsString());

  GrrMessage request_3;
  ASSERT_TRUE(google::protobuf::TextFormat::ParseFromString(
      "request_id: 3 name: 'SlowAction'", &request_3));

  inbox.AddMessage(request_1);
  inbox.AddMessage(request_2);
  inbox.AddMessage(request_3);

  const auto results = testing::GetMessagesExact(4, &outbox);
  // Expect one status for each action.
  std::set<int> statuses_seen;
  for (const auto& result : results) {
    if (result.type() == GrrMessage::STATUS) {
      statuses_seen.insert(result.request_id());
    }
    switch (result.request_id()) {
      case 1: {
        EXPECT_EQ(result.name(), "SlowAction");
        EXPECT_EQ(result.response_id(), 1);
        EXPECT_EQ(result.type(), GrrMessage::STATUS);
      } break;
      case 2: {
        EXPECT_EQ(result.name(), "FastAction");
        if (result.response_id() == 1) {
          EXPECT_EQ(result.type(), GrrMessage::MESSAGE);
          PathSpec path_spec_result;
          EXPECT_TRUE(path_spec_result.ParseFromString(result.args()));
          EXPECT_EQ(path_spec_result.path(), "/etc/passwd");
        } else {
          EXPECT_EQ(result.response_id(), 2);
          EXPECT_EQ(result.type(), GrrMessage::STATUS);
        }
      } break;
      case 3: {
        EXPECT_EQ(result.name(), "SlowAction");
        EXPECT_EQ(result.response_id(), 1);
        EXPECT_EQ(result.type(), GrrMessage::STATUS);
      } break;
    }
  }
  EXPECT_EQ(statuses_seen.size(), 3);
}
}  // namespace grr
