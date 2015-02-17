#ifndef GRR_CPP_CLIENT_LOGGING_CONTROL_H
#define GRR_CPP_CLIENT_LOGGING_CONTROL_H

#include "base.h"

namespace grr {

// A class which can accept log messages and do something with them.
class LogSink {
 public:
  virtual ~LogSink() {}
  virtual void Log(LogLevel level, const char* filename, int line,
		   const std::string& message) = 0;
};

// Provides static global methods to control logging.
class LogControl {
 public:
  // Add sink to the system so that it will see all log messages.
  static void AddLogSink(LogSink* sink);

  // Remove sink from the system.
  static void RemoveLogSink(LogSink* sink);
};

}
#endif  // GRR_CPP_CLIENT_LOGGING_CONTROL_H
