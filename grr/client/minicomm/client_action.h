#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/config.h"
#include "grr/client/minicomm/message_queue.h"

namespace grr {
class ActionContext;

// Represents a client action.
class ClientAction {
 public:
  ClientAction() {}
  ~ClientAction() {}

  // Attempt to handle the request contained in context. Should send all
  // necessary responses, except for the final status message.
  virtual void ProcessRequest(ActionContext* context) = 0;
};

// Contains the data and helper methods to read a request and report back to the
// server.
class ActionContext {
 public:
  ActionContext(const GrrMessage& grr_message, MessageQueue* outbox,
                ClientConfig* config)
      : response_id_(1),
        outbox_(outbox),
        grr_message_(grr_message),
        config_(config) {}

  ~ActionContext() {}

  // The message which we are responding to.
  const GrrMessage& Message() const { return grr_message_; }

  // Helper method to populate an args protocol buffer. Returns true on success,
  // sets an error status on failure.
  bool PopulateArgs(google::protobuf::Message* args);

  // Helper method to send a response to the server for the current
  // request. Encodes payload into the response's args field. Returns true on
  // success, otherwise returns false and sets an error status.
  bool SendResponse(const google::protobuf::Message& payload,
                    GrrMessage::Type type);

  // Fail this action, setting GENERIC_ERROR status with error_message.
  void SetError(const std::string& error_message);

  // Send a message to the server verbatim.
  void SendMessage(const GrrMessage& message) { outbox_->AddMessage(message); }

  // Report the current status.
  const GrrStatus& Status() const { return status_; }

  // Reference to ClientConfig.
  const ClientConfig& Config() const {
    GOOGLE_DCHECK_NE(config_, nullptr);
    return *config_;
  }

 private:
  ClientConfig* const config_;
  MessageQueue* const outbox_;
  const GrrMessage grr_message_;

  // The next response id that we should use.
  int response_id_;

  // The status of this action.
  GrrStatus status_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTION_H_
