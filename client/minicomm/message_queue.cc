#include "grr/client/minicomm/message_queue.h"

#include <algorithm>
#include <string>

namespace grr {
void MessageQueue::AddMessage(const GrrMessage& message) {
  std::unique_lock<std::mutex> l(lock_);
  const int arg_size = message.args().size();
  if (!CanAddMessage(arg_size)) {
    queue_shrunk_.wait(
        l, [this, arg_size] { return this->CanAddMessage(arg_size); });
  }
  args_size_ += arg_size;
  messages_.emplace_back(message);
  l.unlock();
  queue_grew_.notify_all();
}

void MessageQueue::AddPriorityMessage(const GrrMessage& message) {
  std::unique_lock<std::mutex> l(lock_);
  args_size_ += message.args().size();
  messages_.emplace_front(message);
  l.unlock();
  queue_grew_.notify_all();
}

std::vector<GrrMessage> MessageQueue::GetMessages(int max_message_count,
                                                  int max_args_size,
                                                  bool blocking) {
  std::unique_lock<std::mutex> l(lock_);
  if (messages_.empty() && blocking) {
    queue_grew_.wait(l, [this] { return !this->messages_.empty(); });
  }
  int count = 0;
  int args_size = 0;
  for (const GrrMessage& m : messages_) {
    const int new_count = count + 1;
    const int new_args_size = args_size + m.args().size();
    if (count == 0 ||
        (new_count <= max_message_count && new_args_size <= max_args_size)) {
      // There is room to include this message.
      count = new_count;
      args_size = new_args_size;
    } else {
      break;
    }
  }
  std::vector<GrrMessage> result;
  result.reserve(count);
  for (int i = 0; i < count; i++) {
    result.emplace_back(messages_.front());
    messages_.pop_front();
  }
  args_size_ -= args_size;

  l.unlock();
  queue_shrunk_.notify_all();
  return result;
}

int MessageQueue::current_message_count() const {
  std::unique_lock<std::mutex> l(lock_);
  return messages_.size();
}

int MessageQueue::current_args_size() const {
  std::unique_lock<std::mutex> l(lock_);
  return args_size_;
}

bool MessageQueue::CanAddMessage(int new_args_size) {
  return messages_.size() == 0 ||
         (messages_.size() < max_message_count_ &&
          args_size_ + new_args_size <= max_args_size_);
}
}  // namespace grr
