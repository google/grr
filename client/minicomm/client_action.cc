#include "grr/client/minicomm/client_action.h"

namespace grr {

bool ActionContext::PopulateArgs(google::protobuf::Message* args) {
  if (!grr_message_.has_args()) {
    SetError("Expected args of type: " + args->GetTypeName() +
             ", but no args provided.");
    return false;
  }
  if (args->GetTypeName() != grr_message_.args_rdf_name()) {
    SetError("Expected args of type: " + args->GetTypeName() +
             ", but received args of type: " + grr_message_.args_rdf_name());
    return false;
  }
  if (!args->ParseFromString(grr_message_.args())) {
    SetError("Unable to parse args.");
    return false;
  }
  return true;
}

bool ActionContext::SendResponse(const google::protobuf::Message& payload,
                                 GrrMessage::Type type) {
  GrrMessage message;
  message.set_args_rdf_name(payload.GetTypeName());
  if (!payload.SerializeToString(message.mutable_args())) {
    SetError("Unable to serialize response.");
    return false;
  }
  // Leave unset if we were passed the default.
  if (type != message.type()) {
    message.set_type(type);
  }
  message.set_name(grr_message_.name());
  message.set_request_id(grr_message_.request_id());
  message.set_response_id(response_id_++);
  message.set_session_id(grr_message_.session_id());
  message.set_task_id(grr_message_.task_id());

  SendMessage(message);
  return true;
}

void ActionContext::SetError(const std::string& error_message) {
  status_.set_status(GrrStatus::GENERIC_ERROR);
  status_.set_error_message(error_message);
}
}  // namespace grr
