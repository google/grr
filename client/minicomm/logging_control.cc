#include "logging_control.h"

#include <vector>
#include <algorithm>
#include <mutex>

using google::protobuf::LogHandler;

namespace grr {
namespace {

class DefaultLogSink : public LogSink {
 public:
  void Log(LogLevel level, const char* filename, int line,
           const std::string& message) override {
    static const char* level_names[] = { "I", "W", "E", "F" };

    // We use fprintf() instead of cerr because we want this to work at static
    // initialization time.
    fprintf(stderr, "[%s %s:%d] %s\n",
            level_names[level], filename, line, message.c_str());
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

void LogControl::Initialize() {
  LogManager::Singleton();
}

void LogControl::AddLogSink(LogSink* sink) {
  LogManager::Singleton()->AddLogSink(sink);
}

void LogControl::RemoveLogSink(LogSink* sink) {
  LogManager::Singleton()->RemoveLogSink(sink);
}
}
