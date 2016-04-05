// Copyright 2012 Google Inc
// All Rights Reserved.

#ifndef GRR_CLIENT_NANNY_EVENT_LOGGER_H_
#define GRR_CLIENT_NANNY_EVENT_LOGGER_H_

#include <string>                       // for string

#ifdef WIN32
#define DISALLOW_COPY_AND_ASSIGN(TypeName) \
  TypeName(const TypeName&);               \
  void operator=(const TypeName&)
#else
#include "base/macros.h"                // for DISALLOW_COPY_AND_ASSIGN
#endif

// Windows uses evil macros which interfer with proper C++.
#ifdef GetCurrentTime
#undef GetCurrentTime
#endif

namespace grr {

// A class which manages logging to a suitable event log. The specific event log
// is platform dependent. For example, the windows implementation uses the
// windows event log, the Linux one will use syslog.
class EventLogger {
 public:
  // Default logger suppresses identical messages within a 60 second period.
  EventLogger()
      : last_message_(),
        last_message_time_(0),
        message_suppression_time_(60) {}

  virtual ~EventLogger();

  // Generate an event log message with the same semantics as printf.
  virtual void Log(const char *fmt, ...);

  // Sets the time in seconds for which we will suppress any duplicate messages
  // that match the most recently printed message.
  void set_message_suppression_time(int suppression_time) {
    message_suppression_time_ = suppression_time;
  }

 protected:
  // Write the message to the appropriate platform-specific log.
  virtual void WriteLog(std::string message) = 0;

  // Gets the current wall clock time in seconds since the epoch.
  virtual time_t GetCurrentTime() = 0;

 private:
  // The last message we wrote to the log.
  std::string last_message_;

  // When the last message was written (seconds since Epoch).
  time_t last_message_time_;

  // If an identical message is generated within this many seconds, it is
  // suppressed.
  int message_suppression_time_;

  DISALLOW_COPY_AND_ASSIGN(EventLogger);
};

}  // namespace grr

#endif  // GRR_CLIENT_NANNY_EVENT_LOGGER_H_
