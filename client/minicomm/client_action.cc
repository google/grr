#include "grr/client/minicomm/client_action.h"

namespace grr {

bool ActionContext::PopulateArgs(google::protobuf::Message* args) {
  if (!grr_message_.has_args()) {
    SendError("Expected args of type: " + args->GetTypeName() +
              ", but no args provided.");
    return false;
  }
  if (args->GetTypeName() != grr_message_.args_rdf_name()) {
    SendError("Expected args of type: " + args->GetTypeName() +
              ", but received args of type: " + grr_message_.args_rdf_name());
    return false;
  }
  if (!args->ParseFromString(grr_message_.args())) {
    SendError("Unable to parse args.");
    return false;
  }
  return true;
}

bool ActionContext::SendResponse(const google::protobuf::Message& payload,
                                 GrrMessage::Type type) {
  GrrMessage message;
  message.set_args_rdf_name(payload.GetTypeName());
  if (!payload.SerializeToString(message.mutable_args())) {
    SendError("Unable to serialize response.");
    return false;
  }
  // Leave unset we were passed the default.
  if (type != message.type()) {
    message.set_type(type);
  }
  message.set_request_id(grr_message_.request_id());
  message.set_response_id(grr_message_.response_id());
  message.set_session_id(grr_message_.session_id());
  message.set_task_id(grr_message_.task_id());

  SendMessage(message);
  return true;
}

void ActionContext::SendError(const std::string& error_message) {
  GrrStatus status;
  status.set_status(GrrStatus::GENERIC_ERROR);
  status.set_error_message(error_message);

  // Paranoia check, if status somehow isn't fully initialized,
  // SendResponse could cause an infinite loop.
  if (status.IsInitialized()) {
    SendResponse(status, GrrMessage::STATUS);
  }
}
}  // namespace grr
