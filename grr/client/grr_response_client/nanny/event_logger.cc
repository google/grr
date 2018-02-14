// Copyright 2012 Google Inc
// All Rights Reserved.
// A throttled windows event logger.

#include "grr_response_client/nanny/event_logger.h"

#include <stdarg.h>                     // for va_end, va_list, va_start
#include <stdio.h>                      // for vsnprintf

namespace grr {

// ---------------------------------------------------------
// Event Logger Class
// ---------------------------------------------------------
EventLogger::~EventLogger() {}

void EventLogger::Log(const char *fmt, ...) {
  time_t now = GetCurrentTime();
  char message[4096];
  va_list ap;

  va_start(ap, fmt);
  vsnprintf(message, sizeof(message), fmt, ap);
  va_end(ap);

  if (message == last_message_ &&
      now - last_message_time_ <= message_suppression_time_) {
    return;
  }

  last_message_ = message;
  last_message_time_ = now;

  WriteLog(message);
}

}  // namespace grr
