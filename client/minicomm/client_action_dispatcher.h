#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTION_DISPATCHER_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTION_DISPATCHER_H_

#include <thread>

#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/config.h"
#include "grr/client/minicomm/message_queue.h"

namespace grr {
class ClientActionDispatcher {
 public:
  ClientActionDispatcher(MessageQueue* inbox, MessageQueue* outbox,
                         ClientConfig* config);
  ~ClientActionDispatcher();

  // Setup method. All calls should be made before StartProcessing. Takes
  // ownership.
  void AddAction(const char* name, ClientAction* action);

  // Begins monitoring inbox, and processing messages using added actions.
  void StartProcessing();

  // Returns whether we know how to handle message.
  bool CanHandle(const GrrMessage& message) const;

 private:
  // The thread and method which process actions.
  std::thread processing_thread_;
  void ActionLoop();

  ClientConfig* const config_;
  MessageQueue* const inbox_;
  MessageQueue* const outbox_;

  std::mutex shutting_down_mutex_;
  bool shutting_down_;
  std::map<std::string, std::unique_ptr<ClientAction> > actions_;
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTION_DISPATCHER_H_
