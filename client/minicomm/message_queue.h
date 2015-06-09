#ifndef GRR_CLIENT_MINICOMM_MESSAGE_QUEUE_H_
#define GRR_CLIENT_MINICOMM_MESSAGE_QUEUE_H_

#include <condition_variable>
#include <deque>
#include <mutex>
#include <vector>

#include "grr/proto/jobs.pb.h"

namespace grr {

class MessageQueue {
 public:
  // Create a queue which normally limits itself to max_count records with a
  // total data (args) size of max_args_bytes.
  MessageQueue(int max_count, int max_args_bytes)
      : max_message_count_(max_count),
        max_args_size_(max_args_bytes),
        args_size_(0) {}

  // Adds message to the back of the queue. Will block if there isn't space in
  // the queue, but will add a message to an empty queue, even if args is larger
  // than max_args_size_.
  void AddMessage(const GrrMessage& message);

  // Adds a message to the front of the queue. Will add even if there isn't
  // space in the queue (queue can become oversized).
  void AddPriorityMessage(const GrrMessage& message);

  // Get some messages, up to the listed max count and size, from the front of
  // the queue. If blocking is true, will block until there is at least one
  // message. Will return at least one message, even if it is larger than
  // max_args_size.
  std::vector<GrrMessage> GetMessages(int max_message_count, int max_args_bytes,
                                      bool blocking);

  int current_message_count() const;
  int current_args_size() const;

 private:
  bool CanAddMessage(int new_args_size);
  const int max_message_count_;
  const int max_args_size_;

  int args_size_;
  std::deque<GrrMessage> messages_;

  mutable std::mutex lock_;

  // Condition variables which are notified when the queue changes size.
  std::condition_variable queue_shrunk_;
  std::condition_variable queue_grew_;
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_MESSAGE_QUEUE_H_
