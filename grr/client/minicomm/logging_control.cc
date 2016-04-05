#include "grr/client/minicomm/logging_control.h"

#include <algorithm>
#ifdef ANDROID
#include <android/log.h>
#endif
#include <chrono>
#include <iostream>
#include <mutex>
#include <vector>

using google::protobuf::LogHandler;

namespace grr {
namespace {

using namespace std::chrono;

class DefaultLogSink : public LogSink {
 public:
  void Log(LogLevel level, const char* filename, int line,
           const std::string& message) override {
    const auto current_time = system_clock::now();
    const time_t current_time_t = system_clock::to_time_t(current_time);
    struct tm time;
    gmtime_r(&current_time_t, &time);
    const int usec =
        duration_cast<microseconds>(current_time.time_since_epoch()).count() %
        1000000;
    static const char level_names[] = {'I', 'W', 'E', 'F'};
#ifdef ANDROID
    __android_log_print(ANDROID_LOG_DEBUG, "LOG_GRR",
                        "[%c %02d.%02d %02d:%02d:%02d.%06d %s:%d] %s\n",
                        level_names[level], time.tm_mon, time.tm_mday,
                        time.tm_hour, time.tm_min, time.tm_sec, usec, filename,
                        line, message.c_str());
#else
    fprintf(stderr, "[%c %02d.%02d %02d:%02d:%02d.%06d %s:%d] %s\n",
            level_names[level], time.tm_mon, time.tm_mday, time.tm_hour,
            time.tm_min, time.tm_sec, usec, filename, line, message.c_str());
#endif
  }
};

class LogManager {
 public:
  static LogManager* Singleton() {
    static LogManager* const s = new LogManager();
    return s;
  }
  void Log(LogLevel level, const char* filename, int line,
           const std::string& message) {
    std::unique_lock<std::mutex> l(mutex_);
    for (auto sink : sinks_) {
      sink->Log(level, filename, line, message);
    }
  }
  void AddLogSink(LogSink* sink) {
    if (sink != nullptr) {
      std::unique_lock<std::mutex> l(mutex_);
      sinks_.push_back(sink);
    }
  }
  void RemoveLogSink(LogSink* sink) {
    std::unique_lock<std::mutex> l(mutex_);
    sinks_.erase(std::remove(sinks_.begin(), sinks_.end(), sink), sinks_.end());
  }

 private:
  static void LogToSingleton(LogLevel level, const char* filename, int line,
                             const std::string& message) {
    Singleton()->Log(level, filename, line, message);
  }
  LogManager() {
    std::unique_lock<std::mutex> l(mutex_);
    google::protobuf::SetLogHandler(&LogToSingleton);
    sinks_.push_back(new DefaultLogSink());
  }

  std::mutex mutex_;
  std::vector<LogSink*> sinks_;
};
}  // namespace

void LogControl::Initialize() { LogManager::Singleton(); }

void LogControl::AddLogSink(LogSink* sink) {
  LogManager::Singleton()->AddLogSink(sink);
}

void LogControl::RemoveLogSink(LogSink* sink) {
  LogManager::Singleton()->RemoveLogSink(sink);
}
}  // namespace grr
