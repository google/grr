#include "grr/client/minicomm/client_action_dispatcher.h"

namespace grr {

ClientActionDispatcher::ClientActionDispatcher(MessageQueue* inbox,
                                               MessageQueue* outbox)
    : inbox_(inbox), outbox_(outbox), shutting_down_(false) {}

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

void ClientActionDispatcher::AddAction(ClientAction* action) {
  actions_[action->Name()].reset(action);
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
      ActionContext context(m, outbox_);
      const auto found = actions_.find(m.name());
      if (found == actions_.end()) {
        GOOGLE_LOG(ERROR) << "Unrecognized action: [" << m.name() << "]";
        context.SetError("Unrecognized action: " + m.name());
      } else {
        found->second->ProcessRequest(&context);
      }
      context.SendResponse(context.Status(), GrrMessage::STATUS);
    }
  }
}
}  // namespace grr
