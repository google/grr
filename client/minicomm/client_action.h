#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/message_queue.h"

namespace grr {

// Contains the data and helper methods to read a request and report back to the
// server.
class ActionContext {
 public:
  ActionContext(const GrrMessage& grr_message, MessageQueue* outbox)
      : outbox_(outbox), grr_message_(grr_message) {}

  ~ActionContext() {}

  // The message which we are responding to.
  const GrrMessage& Message() const { return grr_message_; }

  // Helper method to populate an args protocol buffer. Returns true on success,
  // sends an error to the server on failure.
  bool PopulateArgs(google::protobuf::Message* args);

  // Helper method to create a response GrrMesssage protocol buffer, encoding
  // payload into its args field. Returns true on success, returns false and
  // sends an error to the server if the payload doesn't serialize.
  bool SendResponse(const google::protobuf::Message& payload,
                    GrrMessage::Type type);

  // Report an error processing the current request.
  void SendError(const std::string& error_message);

  // Send a message to the server verbatim.
  void SendMessage(const GrrMessage& message) { outbox_->AddMessage(message); }

 private:
  MessageQueue* const outbox_;
  const GrrMessage grr_message_;
};

// Represents a client action.
class ClientAction {
 public:
  ClientAction() {}
  ~ClientAction() {}

  // Returns the name of the ClientAction. Used to recognize requests for the
  // action.
  virtual const char* Name() = 0;

  virtual void ProcessRequest(ActionContext* context) = 0;
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_
