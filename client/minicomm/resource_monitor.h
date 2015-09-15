#ifndef GRR_CLIENT_MINICOMM_RESOURCE_MONITOR_H_
#define GRR_CLIENT_MINICOMM_RESOURCE_MONITOR_H_

#endif  // GRR_CLIENT_MINICOMM_RESOURCE_MONITOR_H_

#include <math.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/time.h>
#include <sys/resource.h>

#include <atomic>
#include <array>
#include <chrono>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "grr/client/minicomm/message_queue.h"

#include "grr/client/minicomm/base.h"
#include "grr/proto/jobs.pb.h"

namespace grr {

class NetworkResourceMonitor {
 public:
  NetworkResourceMonitor();
  ~NetworkResourceMonitor();

  bool WaitToSend(const std::vector<GrrMessage>&);

 private:
  class Interface {
   public:
    // Do not move COUNT, used as size counter.
    enum Types { ETHERNET = 0, WLAN, MOBILE, COUNT };

    Interface();
    Interface(const uint64,
              const std::chrono::high_resolution_clock::time_point&,
              const double);
    ~Interface();

    bool SendData(const uint64);
    bool Sleep(const uint64);

   private:
    void PassTime(const std::chrono::high_resolution_clock::time_point&);

    uint64 bandwidth_left_;         // amount of bandwidth left in bytes
    double bandwidth_alloc_milli_;  // amount of new bytes available to use as
                                    // bandwidth in one millisecond
    std::chrono::high_resolution_clock::time_point previous_time_;
  };

  Interface::Types GetInterface();
  const std::string GetInterfaceState(const std::string&) const;

  std::array<Interface, Interface::Types::COUNT> interfaces_;
  std::chrono::high_resolution_clock::time_point previous_accessed_;
  Interface::Types previous_response_;
};

class HardwareResourceMonitor {
 public:
  explicit HardwareResourceMonitor(MessageQueue*);
  ~HardwareResourceMonitor();

  void ClientEnrolled();

 private:
  void RefreshLoop();  // Run by ticker_, sends resource usage stats to the
                       // server.

  std::atomic<bool> stop_thread_;
  std::atomic<bool> enrolled_;
  std::thread ticker_;
  MessageQueue* const outbox_;
};

}  // namespace grr
