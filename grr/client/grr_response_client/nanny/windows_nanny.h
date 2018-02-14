// Copyright 2012 Google Inc
// All Rights Reserved.
//

#ifndef GRR_CLIENT_NANNY_WINDOWS_NANNY_H_
#define GRR_CLIENT_NANNY_WINDOWS_NANNY_H_

// This is required in order to force the MSVC compiler to use the old API for
// backwards compatibility. See
// https://msdn.microsoft.com/en-us/library/windows/desktop/ms683219(v=vs.85).aspx
#undef PSAPI_VERSION
#define PSAPI_VERSION 1

// The nanny is a service which runs another child executable, and makes it
// behave. The nanny itself is very simple, hence is it unlikely to leak or
// crash itself, but is used to ensure the more complex child behaves.

// This file implements a Windows-specific ChildController (see description in
// child_controller.h).
#include <windows.h>

// Windows uses evil macros which interfer with proper C++.
#ifdef GetCurrentTime
#undef GetCurrentTime
#endif

#include "grr_response_client/nanny/child_controller.h"

namespace grr {

const TCHAR *kGrrServiceNameKey = TEXT("Nanny.service_name");
const TCHAR *kGrrServiceDescKey = TEXT("Nanny.service_description");

// This is the root of the service configuration branch in the
// registry. It is normally passed through the --service_key command
// line arg.
TCHAR* kGrrServiceRegistry = NULL;


// A registry value specifying the child that will be run.
const TCHAR* kGrrServiceBinaryChildKey = TEXT("Nanny.child_binary");
const TCHAR* kGrrServiceBinaryCommandLineKey = TEXT("Nanny.child_command_line");

// A backup binary location, in case the primary binary failed to start.
const TCHAR* kGrrServiceBinaryChildAlternate = TEXT(
    "Nanny.child_last_known_good");

// The registry value which is updated for each heartbeat. It is a REG_DWORD and
// stores a unix epoch time.
const TCHAR* kGrrServiceHeartbeatTimeKey = TEXT("Nanny.heartbeat");

// The registry value which is updated for the nanny messages.
const TCHAR* kGrrServiceNannyMessageKey = TEXT("Nanny.message");

// The registry value which is updated for the nanny status.
const TCHAR* kGrrServiceNannyStatusKey = TEXT("Nanny.status");


// ---------------------------------------------------------
// StdOutLogger: A logger to stdout.
// ---------------------------------------------------------
class StdOutLogger : public grr::EventLogger {
 public:
  StdOutLogger();

  // An optional message can be passed to the constructor to log a single
  // message upon construction. This is useful for one-time log messages to be
  // written to the event log.
  explicit StdOutLogger(const char *message);
  virtual ~StdOutLogger();

 protected:
  void WriteLog(std::string message);
  virtual time_t GetCurrentTime();

 private:
  DISALLOW_COPY_AND_ASSIGN(StdOutLogger);
};


// ---------------------------------------------------------
// WindowsEventLogger: Implementation of the windows event logger.
// ---------------------------------------------------------
class WindowsEventLogger : public grr::StdOutLogger {
 public:
  WindowsEventLogger();

  // An optional message can be passed to the constructor to log a single
  // message upon construction. This is useful for one-time log messages to be
  // written to the event log.
  explicit WindowsEventLogger(const char *message);
  virtual ~WindowsEventLogger();

 protected:
  virtual void WriteLog(std::string message);

 private:
  HANDLE event_source;

  DISALLOW_COPY_AND_ASSIGN(WindowsEventLogger);
};




// We store all configuration specific to the windows nanny in this
// global struct.
class WindowsControllerConfig {
 public:
  WindowsControllerConfig();
  virtual ~WindowsControllerConfig();

  struct grr::ControllerConfig controller_config;

  // A registry key that holds GRR service configuration.
  HKEY service_hive;
  HKEY service_key;

  // The main service key name.
  TCHAR *service_key_name;

  TCHAR service_name[MAX_PATH];
  TCHAR service_description[MAX_PATH];

  // The action to perform. Currently "install".
  TCHAR *action;

  TCHAR child_process_name[MAX_PATH];
  TCHAR child_command_line[MAX_PATH];

  DWORD ParseConfiguration(void);

 private:
  StdOutLogger logger_;
  DWORD ReadValue(const TCHAR *value, TCHAR *dest, DWORD len);

  DISALLOW_COPY_AND_ASSIGN(WindowsControllerConfig);
};

// The global configuration object. Will be initialized by the main()
// function.
WindowsControllerConfig *kNannyConfig = NULL;

}  // namespace grr

#endif  // GRR_CLIENT_NANNY_WINDOWS_NANNY_H_
