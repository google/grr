#include "grr/client/minicomm/resource_monitor.h"

#include <fstream>

#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/util.h"

namespace grr {

namespace {
uint64 GetUsageTime(const timeval& u) {
  return static_cast<uint64>(u.tv_sec) * static_cast<uint64>(1e6) +
         static_cast<uint64>(u.tv_usec);
}
}  // namespace

const std::string NetworkResourceMonitor::GetInterfaceState(
    const std::string& interface) const {
  std::ifstream file("/sys/class/net/" + interface + "/operstate");
  if (file.good() == false) return "unavailable";
  std::string state;
  file >> state;
  return state;
}

NetworkResourceMonitor::Interface::Types
NetworkResourceMonitor::GetInterface() {
  const auto new_time = std::chrono::high_resolution_clock::now();

  if (std::chrono::duration_cast<std::chrono::milliseconds>(new_time -
                                                            previous_accessed_)
          .count() < 5000)  // 5 seconds
    return previous_response_;

  previous_accessed_ = new_time;
  if (GetInterfaceState("en0") == "up" || GetInterfaceState("em1") == "up") {
    return previous_response_ = Interface::Types::ETHERNET;
  }

  if (GetInterfaceState("wlan0") == "up") {
    return previous_response_ = Interface::Types::WLAN;
  }

  return previous_response_ = Interface::Types::MOBILE;
}

bool NetworkResourceMonitor::WaitToSend(const std::vector<GrrMessage>& data) {
  uint64 data_size = 0;
  for (const auto& message : data) {
    data_size += message.ByteSize();
  }

  data_size = data_size * 1.20;  // http overhead ~ 20% (pessimistic)

  // Hangs untill some interface becomes available and there is enough bandwith
  // to be used on that interface.
  while (1) {
    const Interface::Types interface = GetInterface();

    if (interfaces_[interface].SendData(data_size) == true) {
      return true;
    } else {
      if (interfaces_[interface].Sleep(data_size) == false) {
        return false;  // sleep would be too long
      }
    }
  }
}

NetworkResourceMonitor::NetworkResourceMonitor() {
  auto test_time = std::chrono::high_resolution_clock::now();

  interfaces_[Interface::Types::ETHERNET] =
      Interface(0, test_time, 100);  // ~200GB per month

  interfaces_[Interface::Types::WLAN] =
      Interface(0, test_time, 1);  // ~2GB per month

  interfaces_[Interface::Types::MOBILE] =
      Interface(0, test_time, 1e-1);  // ~200MB per month
}

NetworkResourceMonitor::~NetworkResourceMonitor() {}

NetworkResourceMonitor::Interface::Interface(
    const uint64 bandwidth,
    const std::chrono::high_resolution_clock::time_point& updated,
    const double bandwidth_alloc)
    : bandwidth_left_(bandwidth),
      previous_time_(updated),
      bandwidth_alloc_milli_(bandwidth_alloc) {}

void NetworkResourceMonitor::Interface::PassTime(
    const std::chrono::high_resolution_clock::time_point& new_time) {
  auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                     new_time - previous_time_)
                     .count();

  bandwidth_left_ += elapsed * bandwidth_alloc_milli_;
  previous_time_ = new_time;
}

NetworkResourceMonitor::Interface::Interface() {}
NetworkResourceMonitor::Interface::~Interface() {}

bool NetworkResourceMonitor::Interface::Sleep(const uint64 data_size) {
  if (data_size <= bandwidth_left_) return true;

  // How long should the thread sleep to accumulate bandwidth, in
  // milliseconds.
  const uint64 diff =
      1 + (data_size - bandwidth_left_) / bandwidth_alloc_milli_;

  GOOGLE_LOG(INFO) << "Size of data waiting to be sent: "
                   << static_cast<int>(data_size / 1024) << "kb";

  if (diff > 60 * 1000) {  // 1 min
    return false;  // this packet would take up too much bandwidth at once
  }

  GOOGLE_LOG(INFO) << "Sleeping for: " << static_cast<double>(diff / 1000.)
                   << "seconds.";
  std::this_thread::sleep_for(std::chrono::milliseconds(diff));
  return true;
}

bool NetworkResourceMonitor::Interface::SendData(const uint64 data_size) {
  PassTime(std::chrono::high_resolution_clock::now());
  if (bandwidth_left_ >= data_size) {
    bandwidth_left_ -= data_size;
    return true;
  }
  return false;
}

void HardwareResourceMonitor::RefreshLoop() {
  rusage previous_usage;
  getrusage(RUSAGE_SELF, &previous_usage);

  auto previous_time = std::chrono::high_resolution_clock::now();
  CpuSample previous_cpu_sample;

  while (stop_thread_ == false) {
    std::this_thread::sleep_for(
        std::chrono::milliseconds(1 * 1000));  // sleep for one second

    rusage current_usage;
    if (getrusage(RUSAGE_SELF, &current_usage) == -1) {
      // Error occured while getting rusage.
      continue;
    }

    const auto current_time = std::chrono::high_resolution_clock::now();
    const uint64 elapsed_time =
        std::chrono::duration_cast<std::chrono::microseconds>(current_time -
                                                              previous_time)
            .count();

    const uint64 current_user_usage_time = GetUsageTime(current_usage.ru_utime);
    const uint64 previous_user_usage_time =
        GetUsageTime(previous_usage.ru_utime);

    const uint64 current_system_usage_time =
        GetUsageTime(current_usage.ru_stime);
    const uint64 previous_system_usage_time =
        GetUsageTime(previous_usage.ru_stime);

    const uint64 user_usage_time =
        current_user_usage_time - previous_user_usage_time;
    const uint64 system_usage_time =
        current_system_usage_time - previous_system_usage_time;

    previous_time = current_time;
    previous_usage = current_usage;

    // Percentage representing amount of time cpu spends in this
    // agent. This number could be higher than 100 (multiple cores).

    const double cpu_user_usage = static_cast<double>(user_usage_time) /
                                  static_cast<double>(elapsed_time) * 100.0;

    const double cpu_system_usage = static_cast<double>(system_usage_time) /
                                    static_cast<double>(elapsed_time) * 100.0;

    if (cpu_user_usage + cpu_system_usage < 1e-5) {
      // It appears that the rusage wasn't updated in this moment so there is
      // no
      // difference between two time points.
      continue;
    }

    CpuSample current_cpu_sample;
    current_cpu_sample.set_user_cpu_time(cpu_user_usage);
    current_cpu_sample.set_system_cpu_time(cpu_system_usage);
    current_cpu_sample.set_cpu_percent(cpu_user_usage + cpu_system_usage);

    current_cpu_sample.set_timestamp(
        std::chrono::duration_cast<std::chrono::microseconds>(
            current_time.time_since_epoch())
            .count());

    // If the difference between two usages is smaller than 5% of usage and
    // time
    // between two updates is smaller than 10 seconds than there is no need to
    // send new cpu_usage.

    if (current_cpu_sample.timestamp() - previous_cpu_sample.timestamp() <
            static_cast<uint64>(1e6) * static_cast<uint64>(10) &&
        fabs(current_cpu_sample.cpu_percent() -
             previous_cpu_sample.cpu_percent()) < 5.0) {
      continue;
    }

    ClientStats res;
    res.add_cpu_samples();
    *res.mutable_cpu_samples(0) = current_cpu_sample;

    GrrMessage stats;
    res.SerializeToString(stats.mutable_args());

    stats.set_name("GetClientStatsAuto");
    stats.set_args_rdf_name("ClientStats");
    stats.set_session_id("F:Stats");
    stats.set_response_id(0);
    stats.set_request_id(0);
    stats.set_task_id(0);

    if (enrolled_) outbox_->AddMessage(stats);

    previous_cpu_sample = current_cpu_sample;
  }
}

void HardwareResourceMonitor::ClientEnrolled() { enrolled_ = true; }

HardwareResourceMonitor::HardwareResourceMonitor(MessageQueue* outbox)
    : outbox_(outbox), stop_thread_(false), enrolled_(false) {
  ticker_ = std::thread(&HardwareResourceMonitor::RefreshLoop, this);
}

HardwareResourceMonitor::~HardwareResourceMonitor() {
  stop_thread_ = true;
  if (ticker_.joinable()) {
    ticker_.join();
  }
}

}  // namespace grr
