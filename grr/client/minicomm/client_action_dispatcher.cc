#include "grr/client/minicomm/client_action_dispatcher.h"

namespace grr {

ClientActionDispatcher::ClientActionDispatcher(MessageQueue* inbox,
                                               MessageQueue* outbox,
                                               ClientConfig* config)
    : inbox_(inbox), outbox_(outbox), shutting_down_(false), config_(config) {}

ClientActionDispatcher::~ClientActionDispatcher() {
  {
    std::unique_lock<std::mutex> l(shutting_down_mutex_);
    shutting_down_ = true;
  }
  if (processing_thread_.joinable()) {
    // Worker thread might now be waiting to read from the inbox. Add an empty
    // message to unstick it.
    inbox_->AddMessage(GrrMessage());
    processing_thread_.join();
  }
}

void ClientActionDispatcher::StartProcessing() {
  processing_thread_ = std::thread([this]() { this->ActionLoop(); });
}

void ClientActionDispatcher::AddAction(const char* name, ClientAction* action) {
  actions_[name].reset(action);
}

bool ClientActionDispatcher::CanHandle(const GrrMessage& message) const {
  return actions_.count(message.name());
}

void ClientActionDispatcher::ActionLoop() {
  while (true) {
    std::vector<GrrMessage> messages = inbox_->GetMessages(100, 100000, true);
    GOOGLE_DCHECK_GT(messages.size(), 0);
    for (const auto& m : messages) {
      {
        std::unique_lock<std::mutex> l(shutting_down_mutex_);
        if (shutting_down_) {
          return;
        }
      }
      ActionContext context(m, outbox_, config_);
      const auto found = actions_.find(m.name());
      if (found == actions_.end()) {
        GOOGLE_LOG(ERROR) << "Unrecognized action: [" << m.name() << "]";
        context.SetError("Unrecognized action: " + m.name());
      } else {
        GOOGLE_LOG(INFO) << "Performing action: " + m.name();
        try {
          found->second->ProcessRequest(&context);
        } catch (std::exception e) {
          // We try to minimize the use of exceptions, but if one happens during
          // a client action we still prefer to report it and not die.
          context.SetError(std::string("Exception in ProcessRequest: ") +
                           e.what());
        }
      }
      context.SendResponse(context.Status(), GrrMessage::STATUS);
    }
  }
}
}  // namespace grr
