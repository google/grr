// Copyright 2012 Google Inc
// All Rights Reserved.
//

#ifndef GRR_CLIENT_NANNY_WINDOWS_NANNY_H_
#define GRR_CLIENT_NANNY_WINDOWS_NANNY_H_

// The nanny is a service which runs another child executable, and makes it
// behave. The nanny itself is very simple, hence is it unlikely to leak or
// crash itself, but is used to ensure the more complex child behaves.

// This file implements a Windows-specific ChildController (see description in
// child_controller.h).
#include <windows.h>

#include "grr/client/nanny/child_controller.h"

TCHAR kGrrServiceName[] = TEXT("GRR");
TCHAR kGrrServiceDesc[] = TEXT("The GRR Monitoring Service");

// A registry key that holds GRR service configuration.
#define GRR_SERVICE_REGISTRY_HIVE HKEY_LOCAL_MACHINE

const TCHAR* kGrrServiceRegistry = TEXT("SOFTWARE\\Google\\GRR");

// A registry value specifying the child that will be run.
const TCHAR* kGrrServiceBinaryChild = TEXT("ChildBinary");
const TCHAR* kGrrServiceBinaryCommandLine = TEXT("ChildCommandLine");

// A backup binary location, in case the primary binary failed to start.
const TCHAR* kGrrServiceBinaryChildAlternate = TEXT("ChildBinaryLastKnownGood");

// The registry value which is updated for each heartbeat. It is a REG_DWORD and
// stores a unix epoch time.
const TCHAR* kGrrServiceHeartbeatTime = TEXT("Heartbeat");

// The registry value which is updated for the nanny messages.
const TCHAR* kGrrServiceNannyMessage = TEXT("NannyMessage");

// The registry value which is updated for the nanny status.
const TCHAR* kGrrServiceNannyStatus = TEXT("NannyStatus");

// Configuration of nanny policies.
const struct grr::ControllerConfig kNannyConfig = {
  // Child must stay dead for this many seconds.
  60,  // resurrection_period

  // If we receive no heartbeats from the client in this long, child is killed.
  180,  // unresponsive_kill_period
  60 * 60 * 24,  // event_log_message_suppression
  0,  // failure_count, not yet used
  1024 * 1024 * 1024,  // client memory limit
};

#endif  // GRR_CLIENT_NANNY_WINDOWS_NANNY_H_
