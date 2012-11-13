// Copyright 2012 Google Inc
// All Rights Reserved.
//
//
// This windows service installation code is inspired from the MSDN article:
// http://msdn.microsoft.com/en-us/library/windows/desktop/bb540475(v=vs.85).aspx

#include "grr/client/nanny/windows_nanny.h"

#include <Psapi.h>
#include <stdio.h>
#include <tchar.h>
#include <time.h>
// TODO(user): On Windows 8 this should be replaced by Processthreadsapi.h
#include <WinBase.h>
#include <windows.h>

#include <memory>
#include <string>

#include "grr/client/nanny/child_controller.h"
#include "grr/client/nanny/event_logger.h"

using ::grr::EventLogger;

namespace {

// Global objects for synchronization.
SERVICE_STATUS g_service_status;
SERVICE_STATUS_HANDLE g_service_status_handler;
HANDLE g_service_stop_event = NULL;

// ---------------------------------------------------------
// WindowsEventLogger: Implementation of the windows event logger.
// ---------------------------------------------------------
class WindowsEventLogger : public grr::EventLogger {
 public:
  WindowsEventLogger();

  // An optional message can be passed to the constructor to log a single
  // message upon construction. This is useful for one-time log messages to be
  // written to the event log.
  explicit WindowsEventLogger(const char *message);
  virtual ~WindowsEventLogger();

 private:
  HANDLE event_source;
  // Actually write the log file - to be implemented by extensions.
  virtual void WriteLog(std::string message);
  virtual time_t GetCurrentTime();

  DISALLOW_COPY_AND_ASSIGN(WindowsEventLogger);
};

// Open initial connection with event log.
WindowsEventLogger::WindowsEventLogger(const char *message) : EventLogger() {
  // If this fails, we do not log anything. There is nothing else we could do if
  // we cannot log to the event log.
  event_source = RegisterEventSource(NULL, kGrrServiceName);
  if (message) {
    Log(message);
  }
}

WindowsEventLogger::WindowsEventLogger() {
  // If this fails, we do not log anything. There is nothing else we could do if
  // we cannot log to the event log.
  event_source = RegisterEventSource(NULL, kGrrServiceName);
}

// Unregister with the event log.
WindowsEventLogger::~WindowsEventLogger() {
  if (event_source) {
    DeregisterEventSource(event_source);
  }
}

// Gets the current epoch time..
time_t WindowsEventLogger::GetCurrentTime() {
  return time(NULL);
}

// Write the log message to the event log.
void WindowsEventLogger::WriteLog(std::string message) {
  const TCHAR *strings[2];

  strings[0] = kGrrServiceName;
  strings[1] = message.c_str();

  if (message.find("%") != std::string::npos) {
    strings[1] = "Invalid event message (Contains %%)";
  }

  if (event_source) {
    ReportEvent(event_source,         // event log handle
                EVENTLOG_ERROR_TYPE,  // event type
                0,                    // event category
                1,                    // event identifier
                NULL,                 // no security identifier
                2,                    // size of lpszStrings array
                0,                    // no binary data
                strings,              // array of strings
                NULL);                // no binary data
  }
};

// ---------------------------------------------------------
// ServiceKey: A scoped object to manage access to the nanny
// registry keys.
// ---------------------------------------------------------
class ServiceKey {
 public:
  ServiceKey();
  ~ServiceKey();

  // Returns the service key or NULL if key could not be opened.
  HKEY GetServiceKey();

 private:
  HKEY key;
  WindowsEventLogger logger_;

  DISALLOW_COPY_AND_ASSIGN(ServiceKey);
};

ServiceKey::ServiceKey()
    : key(NULL),
      logger_(NULL) {}

// Opens the service key.
HKEY ServiceKey::GetServiceKey() {
  if (key) {
    return key;
  }

  // We need to turn on 64 bit access as per
  // http://msdn.microsoft.com/en-us/library/aa384129(v=VS.85).aspx
  HRESULT result = RegOpenKeyEx(HKEY_LOCAL_MACHINE,
                                kGrrServiceRegistry,
                                0,
                                KEY_WOW64_64KEY | KEY_READ | KEY_WRITE,
                                &key);
  if (result != ERROR_SUCCESS) {
    key = 0;
    TCHAR errormsg[1024];
    FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, 0, result, 0, errormsg,
                  1024, NULL);
    logger_.Log("Unable to open service key (%s): %s", kGrrServiceRegistry,
                errormsg);
    return NULL;
  }

  return key;
}

ServiceKey::~ServiceKey() {
  if (key) {
    RegCloseKey(key);
  }
}


// ---------------------------------------------------------
// WindowsChildProcess: Implementation of the windows child controller.
// ---------------------------------------------------------
class WindowsChildProcess : public grr::ChildProcess {
 public:
  WindowsChildProcess();
  virtual ~WindowsChildProcess();

  // Kills the child.
  virtual void KillChild(std::string msg);

  // Create the child process.
  virtual bool CreateChildProcess();

  // Check the last heart beat from the child.
  virtual time_t GetHeartBeat();

  virtual time_t GetCurrentTime();

  virtual EventLogger *GetEventLogger();

  virtual void SetNannyMessage(std::string msg);

  virtual void SetNannyStatus(std::string msg);

  virtual void ClearHeartbeat();

  virtual size_t GetMemoryUsage();

  virtual bool IsAlive();

 private:
  PROCESS_INFORMATION child_process;
  WindowsEventLogger logger_;

  DISALLOW_COPY_AND_ASSIGN(WindowsChildProcess);
};

EventLogger *WindowsChildProcess::GetEventLogger() {
  return &logger_;
};


// Kills the child.
void WindowsChildProcess::KillChild(std::string msg) {
  if (child_process.hProcess == NULL)
    return;

  SetNannyStatus(msg);

  TerminateProcess(child_process.hProcess, 0);

  // Wait for the process to exit.
  if (WaitForSingleObject(child_process.hProcess, 2000) != WAIT_OBJECT_0) {
    logger_.Log("Unable to kill child within specified time.");
  }

  CloseHandle(child_process.hProcess);
  CloseHandle(child_process.hThread);
  child_process.hProcess = NULL;
  return;
};

// Returns the last time the child produced a heartbeat.
time_t WindowsChildProcess::GetHeartBeat() {
  ServiceKey key;

  if (!key.GetServiceKey()) {
    return -1;
  }

  DWORD last_heartbeat = 0;
  DWORD data_len = sizeof(last_heartbeat);
  DWORD type;

  if (RegQueryValueEx(key.GetServiceKey(), kGrrServiceHeartBeatTime,
                      0, &type, reinterpret_cast<BYTE*>(&last_heartbeat),
                      &data_len) != ERROR_SUCCESS ||
      type != REG_DWORD || data_len != sizeof(last_heartbeat)) {
    return 0;
  }

  return last_heartbeat;
}

// Clears the heartbeat.
void WindowsChildProcess::ClearHeartbeat() {
  ServiceKey key;

  if (!key.GetServiceKey()) {
    return;
  }

  DWORD value = 0;
  HRESULT result = 0;

  result = RegSetValueEx(key.GetServiceKey(),
                         kGrrServiceHeartBeatTime,
                         0,
                         REG_DWORD,
                         reinterpret_cast<BYTE*>(&value),
                         sizeof(DWORD));
  if (result != ERROR_SUCCESS) {
    TCHAR errormsg[1024];
    FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, 0, result, 0, errormsg,
                  1024, NULL);
    logger_.Log("Unable to clear heartbeat value: %s", errormsg);
  }
};

// This sends a status message back to the server in case of a child kill.
void WindowsChildProcess::SetNannyStatus(std::string msg) {
  ServiceKey key;

  if (!key.GetServiceKey()) {
    return;
  }

  if (RegSetValueExA(key.GetServiceKey(), kGrrServiceNannyStatus, 0, REG_SZ,
                     reinterpret_cast<const BYTE*>(msg.c_str()),
                     msg.size() + 1) != ERROR_SUCCESS) {
    logger_.Log("Unable to set Nanny status (%s).", msg.c_str());
  }
};

// This sends a message back to the server.
void WindowsChildProcess::SetNannyMessage(std::string msg) {
  ServiceKey key;

  if (!key.GetServiceKey()) {
    return;
  }

  if (RegSetValueExA(key.GetServiceKey(), kGrrServiceNannyMessage, 0, REG_SZ,
                     reinterpret_cast<const BYTE*>(msg.c_str()),
                     msg.size() + 1) != ERROR_SUCCESS) {
    logger_.Log("Unable to set Nanny message (%s).", msg.c_str());
  }
};



// Launch the child process.
bool WindowsChildProcess::CreateChildProcess() {
  // Get the binary location from our registry key.
  ServiceKey key;
  TCHAR process_name[MAX_PATH];
  TCHAR command_line[MAX_PATH];
  DWORD process_len = MAX_PATH - 1;
  DWORD command_line_len = MAX_PATH - 1;
  DWORD type;

  if (!key.GetServiceKey()) {
    return false;
  }

  if (RegQueryValueEx(key.GetServiceKey(), kGrrServiceBinaryChild,
                      0, &type, reinterpret_cast<BYTE*>(process_name),
                      &process_len) != ERROR_SUCCESS ||
      type != REG_SZ || process_len >= MAX_PATH) {
    logger_.Log("Unable to open kGrrServiceBinaryChild value.");
    return false;
  }

  // Ensure it is null terminated.
  process_name[process_len] = '\0';

  if (RegQueryValueEx(key.GetServiceKey(), kGrrServiceBinaryCommandLine,
                      0, &type, reinterpret_cast<BYTE*>(command_line),
                      &command_line_len) != ERROR_SUCCESS ||
      type != REG_SZ || command_line_len >= MAX_PATH) {
    logger_.Log("Unable to open kGrrServiceBinaryCommandLine value.");
    return false;
  }

  command_line[command_line_len] = '\0';
  // If the child is already running or we have a handle to it, try to kill it.
  if (IsAlive()) {
    KillChild("Child process restart.");
  }

  // Just copy our own startup info for the child.
  STARTUPINFO startup_info;
  GetStartupInfo(&startup_info);

  // Now try to start it.
  if (!CreateProcess(
          process_name,  // Application Name
          command_line,  // Command line
          NULL,  // Process attributes
          NULL,  //  lpThreadAttributes
          0,  // bInheritHandles
          NULL,  // dwCreationFlags
          NULL,  // lpEnvironment
          NULL,  // lpCurrentDirectory
          &startup_info,  // lpStartupInfo
          &child_process)) {
    logger_.Log("Unable to launch child process: %s %u.", process_name,
                GetLastError());
    return false;
  }

  SetNannyStatus("Child process started.");
  return true;
}


// Return the current date and time in seconds since 1970.
time_t WindowsChildProcess::GetCurrentTime() {
  return time(NULL);
};


size_t WindowsChildProcess::GetMemoryUsage() {
  PROCESS_MEMORY_COUNTERS pmc;
  if (!child_process.hProcess) {
    return 0;
  }

  if (GetProcessMemoryInfo(child_process.hProcess, &pmc, sizeof(pmc))) {
    return (size_t) pmc.WorkingSetSize;
  }
  DWORD res = GetLastError();
  TCHAR errormsg[1024];
  FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, 0, res, 0, errormsg, 1024, NULL);
  logger_.Log("Could not obtain memory information: %s", errormsg);
  return 0;
};

bool WindowsChildProcess::IsAlive() {
  DWORD exit_code = 0;
  if (!child_process.hProcess ||
      !GetExitCodeProcess(child_process.hProcess, &exit_code)) {
    return false;
  }
  return exit_code == STILL_ACTIVE;
};

WindowsChildProcess::WindowsChildProcess()
    : logger_(NULL) {
  ClearHeartbeat();
};


WindowsChildProcess::~WindowsChildProcess() {
  KillChild("Shutting down.");
};


// ---------------------------------------------------------
// Service Setup and installation.
// ---------------------------------------------------------

// ---------------------------------------------------------
// StopService()
//
// Waits a predetermined time for the service to stop.
// Returns false if we failed to stop the service.
// ---------------------------------------------------------
bool StopService(SC_HANDLE service_handle, int time_out) {
  // Send a stop code to the service.
  SERVICE_STATUS_PROCESS service_status_process;
  DWORD bytes_needed;
  time_t start_time = GetTickCount();
  int count = 0;
  WindowsEventLogger logger;

  printf("Stopping Service\n");
  // Make sure the service is not already stopped.

  if (!QueryServiceStatusEx(
          service_handle,
          SC_STATUS_PROCESS_INFO,
          (LPBYTE)&service_status_process,
          sizeof(SERVICE_STATUS_PROCESS),
          &bytes_needed)) {
    logger.Log("QueryServiceStatusEx failed (%d)\n", GetLastError());
    return false;
  }

  if (service_status_process.dwCurrentState == SERVICE_STOPPED) {
    printf("Service is already stopped.\n");
    return true;
  }

  // If a stop is pending, wait for it.

  while (service_status_process.dwCurrentState == SERVICE_STOP_PENDING) {
    printf("%d Service stop pending...\n", count++);

    Sleep(1000);

    if (!QueryServiceStatusEx(
            service_handle,
            SC_STATUS_PROCESS_INFO,
            (LPBYTE)&service_status_process,
            sizeof(SERVICE_STATUS_PROCESS),
            &bytes_needed)) {
      logger.Log("QueryServiceStatusEx failed (%d)\n", GetLastError());
      return false;
    }

    if (service_status_process.dwCurrentState == SERVICE_STOPPED) {
      printf("Service stopped successfully.\n");
      return true;
    }

    if ( GetTickCount() - start_time > 60000 ) {
      logger.Log("Service stop timed out.\n");
      return false;
    }
  }

  if (!ControlService(service_handle, SERVICE_CONTROL_STOP,
                      reinterpret_cast<SERVICE_STATUS*>(
                          &service_status_process))) {
    logger.Log("Unable to stop existing service\n");
    return false;
  }

  // Wait for the service to stop.
  while (service_status_process.dwCurrentState != SERVICE_STOPPED) {
    Sleep(service_status_process.dwWaitHint);
    if (!QueryServiceStatusEx(service_handle,
                              SC_STATUS_PROCESS_INFO,
                              reinterpret_cast<BYTE*>(&service_status_process),
                              sizeof(SERVICE_STATUS_PROCESS),
                              &bytes_needed)) {
      logger.Log("Unable to stop existing service\n");
      return false;
    }

    if (GetTickCount() - start_time > time_out) {
      logger.Log("Wait timed out\n");
      return false;
    }
  }
  printf("Service stopped successfully\n");
  return true;
}


// ---------------------------------------------------------
// InstallService()
//
//     Installs the service. This fuction typically runs in the context of the
// command shell hence printf() works.
// Returns -1 if service failed to be installed, and 0 on success.
// ---------------------------------------------------------
bool InstallService() {
  SC_HANDLE service_control_manager;
  SC_HANDLE service_handle;
  TCHAR module_name[MAX_PATH];
  SERVICE_DESCRIPTION service_descriptor;
  WindowsEventLogger logger(NULL);

  if (!GetModuleFileName(NULL, module_name, MAX_PATH)) {
    logger.Log("Cannot install service.\n");
    return false;
  }

  service_control_manager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
  if (service_control_manager == NULL) {
    logger.Log("Unable to open the Service Control Manager.\n");
    return false;
  }

  // Try to stop and delete an existing service.
  service_handle = OpenService(
      service_control_manager,  // SCM database
      kGrrServiceName,          // name of service
      SERVICE_ALL_ACCESS);      // need delete access

  // Service already exists.
  if (service_handle) {
    if (!StopService(service_handle, 60000)) {
      printf("Service could not be stopped. This is ok if the "
             "service is not already started.\n");
    }
    if (!DeleteService(service_handle)) {
      logger.Log("DeleteService failed (%d)\n", GetLastError());
      CloseServiceHandle(service_handle);
      return false;
    }
    CloseServiceHandle(service_handle);
  }

  // Create the service control entry so we can get started.
  service_handle = CreateService(
      service_control_manager, kGrrServiceName, kGrrServiceName,
      SERVICE_ALL_ACCESS,
      SERVICE_WIN32_OWN_PROCESS,  // Run in our own process.
      SERVICE_AUTO_START,  // Come up on regular startup.
      SERVICE_ERROR_NORMAL,  // If we fail to start, log it and move on.
      module_name, NULL, NULL, NULL,
      // Run as LocalSystem so no username and password.
      NULL, NULL);

  if (service_handle == NULL) {
    logger.Log("CreateService failed (%s)\n", module_name);
    CloseServiceHandle(service_control_manager);
    return false;
  }

  printf("Service successfully installed.\nExecutable: %s\n", module_name);

  // Set the service description.
  service_descriptor.lpDescription = kGrrServiceDesc;
  if (!ChangeServiceConfig2(service_handle, SERVICE_CONFIG_DESCRIPTION,
                            &service_descriptor))
    logger.Log("Could not set service description.\n");

  // Start the service.
  StartService(service_handle, 0, NULL);

  CloseServiceHandle(service_handle);
  CloseServiceHandle(service_control_manager);

  return true;
}

// Send a status report to the service event manager.
void ReportSvcStatus(DWORD current_state, DWORD win32_exit_code,
                     DWORD wait_hint) {
  static DWORD check_point = 1;

  // Fill in the SERVICE_STATUS structure.
  g_service_status.dwCurrentState = current_state;
  g_service_status.dwWin32ExitCode = win32_exit_code;
  g_service_status.dwWaitHint = wait_hint;
  g_service_status.dwControlsAccepted = (
      current_state == SERVICE_START_PENDING ? 0 : SERVICE_ACCEPT_STOP);

  if (current_state == SERVICE_RUNNING ||
      current_state == SERVICE_STOPPED) {
    g_service_status.dwCheckPoint = 0;
  } else {
    g_service_status.dwCheckPoint = check_point++;
  }

  // Report the status of the service to the SCM.
  SetServiceStatus(g_service_status_handler, &g_service_status);
}

// Handles the requested control code.
VOID WINAPI SvcCtrlHandler(DWORD control) {
  switch (control) {
    case SERVICE_CONTROL_STOP:
      ReportSvcStatus(SERVICE_STOP_PENDING, NO_ERROR, 0);

      // Signal the service to stop.
      SetEvent(g_service_stop_event);
      ReportSvcStatus(g_service_status.dwCurrentState, NO_ERROR, 0);
      return;

    case SERVICE_CONTROL_INTERROGATE:
      break;

    default:
      break;
  }
}

// The main function for the service.
VOID WINAPI ServiceMain(DWORD argc, TCHAR *argv) {
  // Registers the handler function for the service.
  g_service_status_handler = RegisterServiceCtrlHandler(kGrrServiceName,
                                                        SvcCtrlHandler);

  if (!g_service_status_handler) {
    WindowsEventLogger("RegisterServiceCtrlHandler");
    return;
  }

  // These SERVICE_STATUS members remain as set here.
  g_service_status.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
  g_service_status.dwServiceSpecificExitCode = 0;

  // Report initial status to the SCM.
  ReportSvcStatus(SERVICE_START_PENDING, NO_ERROR, 3000);

  // Create an event. The control handler function, SvcCtrlHandler, signals this
  // event when it receives the stop control code.
  g_service_stop_event = CreateEvent(
      NULL,    // default security attributes
      TRUE,    // manual reset event
      FALSE,   // not signaled
      NULL);   // no name

  if (!g_service_stop_event) {
    ReportSvcStatus(SERVICE_STOPPED, NO_ERROR, 0);
    return;
  }

  // Create a new child to control.
  WindowsChildProcess child;
  grr::ChildController child_controller(kNannyConfig, &child);

  // Report running status when initialization is complete.
  ReportSvcStatus(SERVICE_RUNNING, NO_ERROR, 0);

  time_t sleep_time = 0;
  // Spin in this loop until the service is stopped.
  while (1) {
    for (unsigned int i = 0; i < sleep_time; i++) {
      // Check every second whether to stop the service.
      if (WaitForSingleObject(g_service_stop_event, 1000) != WAIT_TIMEOUT) {
        child.KillChild("Service stopped.");
        ReportSvcStatus(SERVICE_STOPPED, NO_ERROR, 0);
        return;
      }
      if (child.GetMemoryUsage() > kNannyConfig.client_memory_limit) {
        child.KillChild("Child process exceeded memory limit.");
        break;
      }
      if (!child.IsAlive()) {
                child.SetNannyMessage("Unexpected child process exit!");
        child.KillChild("Child process exited.");
        break;
      }
    }

    // Run the child a bit more.
    sleep_time = child_controller.Run();
  }
}

// The main function.
int _cdecl real_main(int argc, TCHAR *argv[]) {
  // If command-line parameter is "install", install the service.
  // Otherwise, the service is probably being started by the SCM.

  if (argc > 0 && lstrcmpi(argv[1], TEXT("install")) == 0) {
    return InstallService() ? 0 : -1;
  }

  // This table contains all the services provided by this binary.
  SERVICE_TABLE_ENTRY kDispatchTable[] = {
    { kGrrServiceName, reinterpret_cast<LPSERVICE_MAIN_FUNCTION>(ServiceMain) },
    { NULL, NULL }
  };

  // This call returns when the service has stopped.
  // The process should simply terminate when the call returns.
  if (!StartServiceCtrlDispatcher(kDispatchTable)) {
    WindowsEventLogger("StartServiceCtrlDispatcher");
  }
  return 0;
}

}  // namespace

// Main entry point when built as a windows application.
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                   char *lpCmdLine, int nCmdShow) {
  return real_main(__argc, __argv);
}

// Main entry point when build as a console application.
int _tmain(int argc, char *argv[]) {
  return real_main(argc, argv);
};
