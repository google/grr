#include "logging_control.h"

#include <vector>
#include <algorithm>
#include <mutex>

using google::protobuf::LogHandler;

namespace grr {
namespace {

class PassThroughLogSink : public LogSink {
 public:
  explicit PassThroughLogSink(LogHandler* handler) :
    handler_(handler) {}

  void Log(LogLevel level, const char* filename, int line,
      const std::string& message) override {
    handler_(level, filename, line, message);
  }
 private:
  const LogHandler* handler_;
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
    sinks_.push_back(new PassThroughLogSink(google::protobuf::SetLogHandler(&LogToSingleton)));
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
