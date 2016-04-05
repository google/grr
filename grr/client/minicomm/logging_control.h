#ifndef GRR_CLIENT_MINICOMM_LOGGING_CONTROL_H_
#define GRR_CLIENT_MINICOMM_LOGGING_CONTROL_H_

#include "grr/client/minicomm/base.h"

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
  // Initialize the grr client logging system. Should be called before
  // any threads are created.
  static void Initialize();

  // Add sink to the system so that it will see all log messages.
  static void AddLogSink(LogSink* sink);

  // Remove sink from the system.
  static void RemoveLogSink(LogSink* sink);
};
}  // namespace grr
#endif  // GRR_CLIENT_MINICOMM_LOGGING_CONTROL_H_
