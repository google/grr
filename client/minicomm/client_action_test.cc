#include "grr/client/minicomm/client_action.h"

#include "gtest/gtest.h"
#include "google/protobuf/text_format.h"

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/message_queue.h"

namespace grr {

class ActionContextTest : public ::testing::Test {
 public:
  ActionContextTest() : message_queue_(5, 20000) {
    request_message_.set_session_id("Session26");
    request_message_.set_request_id(2600);
    request_message_.set_name("TestAction");
  }

  bool GetOneResponse(GrrMessage* dest) {
    const auto r = message_queue_.GetMessages(5, 20000, true);
    if (r.size() != 1) {
      return false;
    }
    dest->Clear();
    dest->CopyFrom(r[0]);
    return true;
  }

  GrrMessage request_message_;
  MessageQueue message_queue_;
};

TEST_F(ActionContextTest, SendMessage) {
  ActionContext context(request_message_, &message_queue_, nullptr);

  GrrMessage response_message;
  response_message.set_session_id("Session42");
  context.SendMessage(response_message);

  GrrMessage result_message;
  EXPECT_TRUE(GetOneResponse(&result_message));
  EXPECT_EQ(result_message.session_id(), "Session42");
}

TEST_F(ActionContextTest, SendResponse) {
  ActionContext context(request_message_, &message_queue_, nullptr);

  Uname args;
  args.set_system("Nouveau Linux");

  context.SendResponse(args, GrrMessage::MESSAGE);

  GrrMessage result_message;
  EXPECT_TRUE(GetOneResponse(&result_message));
  EXPECT_EQ("Session26", result_message.session_id());
  EXPECT_EQ(1, result_message.response_id());
  EXPECT_EQ(GrrMessage::MESSAGE, result_message.type());

  EXPECT_EQ("Uname", result_message.args_rdf_name());
  EXPECT_EQ(args.SerializeAsString(), result_message.args());

  context.SendResponse(args, GrrMessage::MESSAGE);

  EXPECT_TRUE(GetOneResponse(&result_message));
  EXPECT_EQ("Session26", result_message.session_id());
  EXPECT_EQ(2, result_message.response_id());
  EXPECT_EQ(GrrMessage::MESSAGE, result_message.type());
}

TEST_F(ActionContextTest, SetError) {
  ActionContext context(request_message_, &message_queue_, nullptr);
  EXPECT_EQ(GrrStatus::OK, context.Status().status());

  context.SetError("Unable to fizz or buzz.");

  EXPECT_EQ(GrrStatus::GENERIC_ERROR, context.Status().status());
  EXPECT_EQ("Unable to fizz or buzz.", context.Status().error_message());
}

TEST_F(ActionContextTest, PopulateArgsNoArgs) {
  // Can't import if request doesn't have args attached.
  ActionContext context(request_message_, &message_queue_, nullptr);
  BufferReference ref;
  EXPECT_FALSE(context.PopulateArgs(&ref));

  // Should set an error code.
  EXPECT_EQ(GrrStatus::GENERIC_ERROR, context.Status().status());
  EXPECT_EQ("Expected args of type: BufferReference, but no args provided.",
            context.Status().error_message());
}

TEST_F(ActionContextTest, PopulateArgsBadType) {
  request_message_.set_args_rdf_name("FingerprintRequest");
  request_message_.set_args("");
  ActionContext context(request_message_, &message_queue_, nullptr);
  BufferReference ref;
  EXPECT_FALSE(context.PopulateArgs(&ref));

  // Should set an error code.
  EXPECT_EQ(GrrStatus::GENERIC_ERROR, context.Status().status());
  EXPECT_EQ(
      "Expected args of type: BufferReference, but received args of type: "
      "FingerprintRequest",
      context.Status().error_message());
}

TEST_F(ActionContextTest, PopulateArgsBadData) {
  request_message_.set_args_rdf_name("BufferReference");
  request_message_.set_args("not a protocol buffer");
  ActionContext context(request_message_, &message_queue_, nullptr);
  BufferReference ref;
  EXPECT_FALSE(context.PopulateArgs(&ref));

  // Should set an error code.
  EXPECT_EQ(GrrStatus::GENERIC_ERROR, context.Status().status());
  EXPECT_EQ("Unable to parse args.", context.Status().error_message());
}

TEST_F(ActionContextTest, PopulateArgsEmptyArgs) {
  // Empty args is fine, so long as the rdf name is correct.
  request_message_.set_args_rdf_name("BufferReference");
  request_message_.set_args("");
  ActionContext context(request_message_, &message_queue_, nullptr);
  BufferReference ref;
  EXPECT_TRUE(context.PopulateArgs(&ref));
}

TEST_F(ActionContextTest, PopulateArgsSuccess) {
  BufferReference ref;
  ref.set_offset(2600);
  request_message_.set_args_rdf_name("BufferReference");
  request_message_.set_args(ref.SerializeAsString());

  ref.Clear();
  ActionContext context(request_message_, &message_queue_, nullptr);
  EXPECT_TRUE(context.PopulateArgs(&ref));

  EXPECT_EQ(ref.offset(), 2600);
}

}  // namespace grr
