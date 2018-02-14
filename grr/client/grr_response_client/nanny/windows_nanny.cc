// Copyright 2012 Google Inc
// All Rights Reserved.
//
//
// This windows service installation code is inspired from the MSDN article:
// http://msdn.microsoft.com/en-us/library/windows/desktop/bb540475(v=vs.85).aspx

#include "grr_response_client/nanny/windows_nanny.h"
#include <shellapi.h>
#include <psapi.h>
#include <stdio.h>
#include <tchar.h>
#include <time.h>

/* On Windows 8 or later a separate include is required
 * earlier versions implicitely include winbase.h from windows.h
 */
#if WINVER >= 0x602
#include <Processthreadsapi.h>
#endif
#include <windows.h>

#include <memory>
#include <string>

// Windows uses evil macros which interfere with proper C++.
#ifdef GetCurrentTime
#undef GetCurrentTime
#endif

#include "grr_response_client/nanny/child_controller.h"
#include "grr_response_client/nanny/event_logger.h"

using ::grr::EventLogger;

namespace grr {

// Global objects for synchronization.
SERVICE_STATUS g_service_status;
SERVICE_STATUS_HANDLE g_service_status_handler;
HANDLE g_service_stop_event = NULL;

// Open initial connection with event log.
WindowsEventLogger::WindowsEventLogger(const char *message) : StdOutLogger() {
  // If this fails, we do not log anything. There is nothing else we could do if
  // we cannot log to the event log.
  event_source = RegisterEventSource(NULL, kNannyConfig->service_name);
  if (message) {
    Log(message);
  }
}

WindowsEventLogger::WindowsEventLogger() {
  // If this fails, we do not log anything. There is nothing else we could do if
  // we cannot log to the event log.
  event_source = RegisterEventSource(NULL, kNannyConfig->service_name);
}

// Unregister with the event log.
WindowsEventLogger::~WindowsEventLogger() {
  if (event_source) {
    DeregisterEventSource(event_source);
  }
}

// Write the log message to the event log.
void WindowsEventLogger::WriteLog(std::string message) {
  const TCHAR *strings[2];

  strings[0] = kNannyConfig->service_name;
  strings[1] = message.c_str();

  // TODO(user): change this into overwriting % with place holder chars
  // or equiv
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
}

// ---------------------------------------------------------
// StdOutLogger: A logger to stdout.
// ---------------------------------------------------------
StdOutLogger::StdOutLogger() {}
StdOutLogger::~StdOutLogger() {}
StdOutLogger::StdOutLogger(const char *message) {
  printf("%s\n", message);
}

// Gets the current epoch time..
time_t StdOutLogger::GetCurrentTime() {
  return time(NULL);
}

void StdOutLogger::WriteLog(std::string message) {
  printf("%s\n", message.c_str());
}


// ---------------------------------------------------------
// WindowsChildProcess: Implementation of the windows child controller.
// ---------------------------------------------------------
class WindowsChildProcess : public grr::ChildProcess {
 public:
  WindowsChildProcess();
  virtual ~WindowsChildProcess();

  // The methods below are overridden from Childprocess. See child_controller.h
  // for more information.

  virtual void KillChild(const std::string &msg);

  virtual bool CreateChildProcess();

  virtual time_t GetCurrentTime();

  virtual EventLogger *GetEventLogger();

  virtual void SetNannyMessage(const std::string &msg);

  virtual void SetPendingNannyMessage(const std::string &msg);

  virtual void SetNannyStatus(const std::string &msg);

  virtual time_t GetHeartbeat();

  virtual void ClearHeartbeat();

  virtual void SetHeartbeat(unsigned int value);

  virtual void Heartbeat();

  virtual size_t GetMemoryUsage();

  virtual bool IsAlive();

  virtual bool Started();

  virtual void ChildSleep(unsigned int milliseconds);

 private:
  PROCESS_INFORMATION child_process;
  WindowsEventLogger logger_;
  std::string pendingNannyMsg_;
  DISALLOW_COPY_AND_ASSIGN(WindowsChildProcess);
};

EventLogger *WindowsChildProcess::GetEventLogger() {
  return &logger_;
}


// Kills the child.
void WindowsChildProcess::KillChild(const std::string &msg) {
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
}

// Returns the last time the child produced a heartbeat.
time_t WindowsChildProcess::GetHeartbeat() {
  DWORD last_heartbeat = 0;
  DWORD data_len = sizeof(last_heartbeat);
  DWORD type;

  if (RegQueryValueEx(kNannyConfig->service_key,
                      kGrrServiceHeartbeatTimeKey,
                      0, &type, reinterpret_cast<BYTE*>(&last_heartbeat),
                      &data_len) != ERROR_SUCCESS ||
      type != REG_DWORD || data_len != sizeof(last_heartbeat)) {
    return 0;
  }

  return last_heartbeat;
}

// Clears the heartbeat.
void WindowsChildProcess::ClearHeartbeat() {
  SetHeartbeat(0);
}

// Sets the heartbeat to the current time.
void WindowsChildProcess::Heartbeat() {
  SetHeartbeat((unsigned int)GetCurrentTime());
}

void WindowsChildProcess::SetHeartbeat(unsigned int value) {
  DWORD v = value;
  HRESULT result = 0;

  result = RegSetValueEx(kNannyConfig->service_key,
                         kGrrServiceHeartbeatTimeKey,
                         0,
                         REG_DWORD,
                         reinterpret_cast<BYTE*>(&v),
                         sizeof(DWORD));
  if (result != ERROR_SUCCESS) {
    TCHAR errormsg[1024];
    FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, 0, result, 0, errormsg,
                  1024, NULL);
    logger_.Log("Unable to set heartbeat value: %s", errormsg);
  }
}

// This sends a status message back to the server in case of a child kill.
void WindowsChildProcess::SetNannyStatus(const std::string &msg) {
  if (RegSetValueExA(kNannyConfig->service_key,
                     kGrrServiceNannyStatusKey, 0, REG_SZ,
                     reinterpret_cast<const BYTE*>(msg.c_str()),
                     (DWORD)(msg.size() + 1)) != ERROR_SUCCESS) {
    logger_.Log("Unable to set Nanny status (%s).", msg.c_str());
  }
}

void WindowsChildProcess::SetPendingNannyMessage(const std::string &msg) {
  pendingNannyMsg_ = msg;
}

// This sends a message back to the server.
void WindowsChildProcess::SetNannyMessage(const std::string &msg) {
  if (RegSetValueExA(kNannyConfig->service_key,
                     kGrrServiceNannyMessageKey, 0, REG_SZ,
                     reinterpret_cast<const BYTE*>(msg.c_str()),
                     (DWORD)(msg.size() + 1)) != ERROR_SUCCESS) {
    logger_.Log("Unable to set Nanny message (%s).", msg.c_str());
  }
}



// Launch the child process.
bool WindowsChildProcess::CreateChildProcess() {
  DWORD creation_flags = 0;

  if (pendingNannyMsg_ != "") {
    SetNannyMessage(pendingNannyMsg_);
    pendingNannyMsg_ = "";
  }

  // If the child is already running or we have a handle to it, try to kill it.
  if (IsAlive()) {
    KillChild("Child process restart.");
  }

  // Just copy our own startup info for the child.
  STARTUPINFO startup_info;
  GetStartupInfo(&startup_info);

  // From: http://msdn.microsoft.com/en-us/library/ms682425(VS.85).aspx
  // If this parameter is NULL and the environment block of the parent process
  // contains Unicode characters, you must also ensure that dwCreationFlags
  // includes CREATE_UNICODE_ENVIRONMENT.
#if defined( UNICODE )
  creation_flags = CREATE_UNICODE_ENVIRONMENT;
#endif

  // Now try to start it.
  if (!CreateProcess(
          kNannyConfig->child_process_name,  // Application Name
          kNannyConfig->child_command_line,  // Command line
          NULL,  // Process attributes
          NULL,  //  lpThreadAttributes
          0,  // bInheritHandles
          creation_flags,  // dwCreationFlags
          NULL,  // lpEnvironment
          NULL,  // lpCurrentDirectory
          &startup_info,  // lpStartupInfo
          &child_process)) {
    logger_.Log("Unable to launch child process: %s %u.",
                kNannyConfig->child_process_name,
                GetLastError());
    return false;
  }

  return true;
}


// Return the current date and time in seconds since 1970.
time_t WindowsChildProcess::GetCurrentTime() {
  return time(NULL);
}

void WindowsChildProcess::ChildSleep(unsigned int milliseconds) {
  Sleep(milliseconds);
}


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
}

bool WindowsChildProcess::IsAlive() {
  DWORD exit_code = 0;
  if (!child_process.hProcess) {
    return true;
  }
  if (!GetExitCodeProcess(child_process.hProcess, &exit_code)) {
    return false;
  }
  return exit_code == STILL_ACTIVE;
}

bool WindowsChildProcess::Started() {
  return child_process.hProcess != NULL;
}

WindowsChildProcess::WindowsChildProcess()
    : logger_(NULL), pendingNannyMsg_("") {
  ClearHeartbeat();
}


WindowsChildProcess::~WindowsChildProcess() {
  KillChild("Shutting down.");
}

// -----------------------------------------------------------
// Implementation of the WindowsControllerConfig configuration
// manager.
// -----------------------------------------------------------
WindowsControllerConfig::WindowsControllerConfig()
  : logger_(NULL) {
  // Child must stay dead for this many seconds.
  controller_config.resurrection_period = 60;

  // If we receive no heartbeats from the client in this long, child
  // is killed.
  controller_config.unresponsive_kill_period = 180;

  controller_config.unresponsive_grace_period = 600;

  controller_config.event_log_message_suppression = 60 * 60 * 24;

  controller_config.failure_count_to_revert = 0;
  controller_config.client_memory_limit = 1024 * 1024 * 1024;

  service_hive = HKEY_LOCAL_MACHINE;
  service_key = NULL;
  service_key_name = NULL;

  service_name[0] = '\0';
  service_description[0] = '\0';

  action = TEXT("");
}

WindowsControllerConfig::~WindowsControllerConfig() {
  if (service_key) {
    RegCloseKey(service_key);
  }
}


  // Read a value from the service key and store in dest.
DWORD WindowsControllerConfig::ReadValue(const TCHAR *value_name,
                                         TCHAR *dest, DWORD len) {
  DWORD type;

  if (RegQueryValueEx(service_key,
                      value_name, 0, &type,
                      reinterpret_cast<BYTE*>(dest),
                      &len) != ERROR_SUCCESS ||
      type != REG_SZ || len >= MAX_PATH) {
    logger_.Log("Unable to open value %s.", value_name);
    return ERROR_INVALID_DATA;
  }

  // Ensure it is null terminated.
  dest[len] = '\0';

  return ERROR_SUCCESS;
}


// Parses configuration parameters from __argv.
DWORD WindowsControllerConfig::ParseConfiguration(void) {
  int i;

  for (i = 1; i < __argc; i++) {
    char * parameter = __argv[i];

    if (!strcmp(__argv[i], "--service_key") && i + 1 < __argc) {
      i++;
      service_key_name = __argv[i];
      continue;
    }

    if (!strcmp(__argv[i], "install")) {
      action = __argv[i];
      continue;
    }

    logger_.Log("Unable to parse command line parameter %s", __argv[i]);
    return ERROR_INVALID_DATA;
  }

  if (!service_key_name) {
    logger_.Log("No service key set. Please ensure --service_key is "
                "specified.");
    return ERROR_INVALID_DATA;
  }

  // Try to open the service key now.
  HRESULT result = RegOpenKeyEx(service_hive,
                                service_key_name,
                                0,
                                KEY_READ | KEY_WRITE,
                                &service_key);
  if (result != ERROR_SUCCESS) {
    service_key = 0;
    TCHAR errormsg[1024];

    FormatMessage(FORMAT_MESSAGE_FROM_SYSTEM, 0, result, 0, errormsg,
                  1024, NULL);

    logger_.Log("Unable to open service key (%s): %s", service_key_name,
                errormsg);
    return result;
  }


  // Get the child command line from the service key. The installer
  // should pre-populate this key for us. We fail if we can not find
  // it
  result = ReadValue(kGrrServiceBinaryChildKey, child_process_name,
                     sizeof(child_process_name));
  if (result != ERROR_SUCCESS)
    return result;

  result = ReadValue(kGrrServiceBinaryCommandLineKey, child_command_line,
                     sizeof(child_command_line));
  if (result != ERROR_SUCCESS)
    return result;

  result = ReadValue(kGrrServiceNameKey, service_name, sizeof(service_name));
  if (result != ERROR_SUCCESS)
    return result;

  result = ReadValue(kGrrServiceDescKey, service_description,
                     sizeof(service_description));
  if (result != ERROR_SUCCESS)
    service_description[0] = '\0';

  return ERROR_SUCCESS;
}




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

    if ( GetTickCount() - start_time > time_out ) {
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


#if defined(_WIN32)
typedef BOOL (WINAPI *LPFN_ISWOW64PROCESS) (HANDLE, BOOL*);

// ---------------------------------------------------------
// windows_nanny_IsWow64Process()
//
//     Replace of IsWow64Process function for Windows XP SP1
// and earlier versions. Uses dynamic late binding to call the
// IsWow64Process function or returns False otherwise.
// Returns True if successful, False otherwise
// ---------------------------------------------------------
BOOL windows_nanny_IsWow64Process(HANDLE hProcess, BOOL *Wow64Process) {
  LPFN_ISWOW64PROCESS function = NULL;
  HMODULE library_handle = NULL;
  BOOL result = FALSE;

  if (hProcess == NULL) {
    return FALSE;
  }
  if (Wow64Process == NULL) {
    return FALSE;
  }
  library_handle = LoadLibrary(_T("kernel32.dll"));

  if (library_handle == NULL) {
    return FALSE;
  }
  function = (LPFN_ISWOW64PROCESS) GetProcAddress(
      library_handle, (LPCSTR) "IsWow64Process");

  if (function != NULL) {
    result = function(hProcess, Wow64Process);
  } else {
    *Wow64Process = FALSE;
    result = TRUE;
  }
  if (FreeLibrary(library_handle) != TRUE) {
    result = FALSE;
  }
  return result;
}
#endif

// ---------------------------------------------------------
// InstallService()
//
//     Installs the service. This fuction typically runs in the context of the
// command shell hence printf() works.
// Returns -1 if service failed to be installed, and 0 on success.
// ---------------------------------------------------------
bool InstallService() {
  SC_HANDLE service_control_manager;
  SC_HANDLE service_handle = NULL;
  TCHAR module_name[MAX_PATH];
  SERVICE_DESCRIPTION service_descriptor;
  WindowsEventLogger logger(NULL);
  unsigned int tries = 0;
  DWORD error_code = 0;

#if defined(_WIN32)
  BOOL f64 = FALSE;
  BOOL result = FALSE;

  // Using dynamic late binding here to support WINVER < 0x501
  // TODO(user): remove this function make sure to have the installer
  // detect right platform also see:
  // http://blogs.msdn.com/b/david.wang/archive/2006/03/26/
  // howto-detect-process-bitness.aspx
  result = windows_nanny_IsWow64Process(GetCurrentProcess(), &f64);
  if (result && f64) {
    printf("32 bit installer should not be run on a 64 bit machine!\n");
    return false;
  }
#endif

  if (!GetModuleFileName(NULL, module_name, MAX_PATH)) {
    logger.Log("Cannot install service.\n");
    return false;
  }

  service_control_manager = OpenSCManager(NULL, NULL, SC_MANAGER_ALL_ACCESS);
  if (service_control_manager == NULL) {
    error_code = GetLastError();
    logger.Log("Unable to open Service Control Manager - error code: "
               "0x%08x.\n", error_code);
    return false;
  }

  // module_name contains the path to the service binary and is used in the
  // service command line. kNannyConfig->service_name contains the name of the
  // service.
  std::string command_line(module_name);

  command_line += " --service_key \"";
  command_line += kNannyConfig->service_key_name;
  command_line += "\"";

  service_handle = OpenService(
      service_control_manager,      // SCM database
      kNannyConfig->service_name,   // name of service
      SERVICE_ALL_ACCESS);          // need delete access

  if (service_handle == NULL) {
    error_code = GetLastError();
    if (error_code != ERROR_SERVICE_DOES_NOT_EXIST) {
      printf("Unable to open service: %s unexpected error - error code: "
             "0x%08x.\n", kNannyConfig->service_name, error_code);
      goto on_error;
    }
    // If the service does not exists, create it.
    service_handle = CreateService(
       service_control_manager, kNannyConfig->service_name,
       kNannyConfig->service_name,
       SERVICE_ALL_ACCESS,
       SERVICE_WIN32_OWN_PROCESS,  // Run in our own process.
       SERVICE_AUTO_START,  // Come up on regular startup.
       SERVICE_ERROR_NORMAL,  // If we fail to start, log it and move on.
       command_line.c_str(),  // Command line for the service.
       NULL, NULL, NULL,
       NULL, NULL);  // Run as LocalSystem so no username and password.

    if (service_handle == NULL) {
      error_code = GetLastError();
      printf("Unable to create service: %s - error code: 0x%08x.\n",
             kNannyConfig->service_name, error_code);
        goto on_error;
    }
  } else {
    if (!StopService(service_handle, 60000)) {
      printf("Service could not be stopped. This is ok if the service is not "
             "already started.\n");
    }
    // Set the path to the service binary.
    if (ChangeServiceConfig(
            service_handle, SERVICE_NO_CHANGE,
            SERVICE_NO_CHANGE, SERVICE_NO_CHANGE, command_line.c_str(),
            NULL, NULL, NULL, NULL, NULL, NULL) == 0) {
      error_code = GetLastError();
      printf("Unable to change service: %s configuration - error code: "
             "0x%08x.\n", kNannyConfig->service_name, error_code);
    }
  }

  // Set the service description.
  service_descriptor.lpDescription = kNannyConfig->service_description;
  if (!ChangeServiceConfig2(service_handle, SERVICE_CONFIG_DESCRIPTION,
                            &service_descriptor)) {
    error_code = GetLastError();
    logger.Log("Unable to set service: %s description - error code: 0x%08x.\n",
               kNannyConfig->service_name, error_code);
  }

  // Start the service.
  if (!StartService(service_handle, 0, NULL)) {
    error_code = GetLastError();
    printf("Unable to start service: %s - error code: 0x%08x.\n",
           kNannyConfig->service_name, error_code);
  } else {
    printf("Service: %s started as: %s\n",
           kNannyConfig->service_name, module_name);
  }

  CloseServiceHandle(service_handle);
  CloseServiceHandle(service_control_manager);

  return true;

on_error:
  if (service_handle != NULL) {
    CloseServiceHandle(service_handle);
  }
  if (service_control_manager != NULL) {
    CloseServiceHandle(service_control_manager);
  }
  return false;
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
VOID WINAPI ServiceMain(int argc, LPTSTR *argv) {
  WindowsControllerConfig global_config;
  WindowsEventLogger logger;

  // Parse the configuration and set the global object.
  if (global_config.ParseConfiguration() == ERROR_SUCCESS) {
    kNannyConfig = &global_config;
  } else {
    printf("Unable to parse command line.");
    return;
  }

  // Registers the handler function for the service.
  g_service_status_handler = RegisterServiceCtrlHandler(
    kNannyConfig->service_name, SvcCtrlHandler);

  if (!g_service_status_handler) {
    logger.Log("RegisterServiceCtrlHandler failed.");
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
  grr::ChildController child_controller(kNannyConfig->controller_config,
                                        &child);

  // Report running status when initialization is complete.
  ReportSvcStatus(SERVICE_RUNNING, NO_ERROR, 0);

  child.CreateChildProcess();

  // Give the child process some time to start up. During boot it sometimes
  // takes significantly more time than the unresponsive_kill_period to start
  // the child so we disable checking for heartbeats for a while.
  child.Heartbeat();
  time_t sleep_time = kNannyConfig->controller_config.unresponsive_grace_period;

  // Spin in this loop until the service is stopped.
  while (1) {
    for (unsigned int i = 0; i < sleep_time; i++) {
      // Check every second whether to stop the service.
      if (WaitForSingleObject(g_service_stop_event, 1000) != WAIT_TIMEOUT) {
        child.KillChild("Service stopped.");
        ReportSvcStatus(SERVICE_STOPPED, NO_ERROR, 0);
        return;
      }
      if (child.GetMemoryUsage() >
          kNannyConfig->controller_config.client_memory_limit) {
        child.KillChild("Child process exceeded memory limit.");
        break;
      }
      if (child.Started() && !child.IsAlive()) {
        int shutdown_pending = GetSystemMetrics(SM_SHUTTINGDOWN);
        if (shutdown_pending == 0) {
          child.SetPendingNannyMessage("Unexpected child process exit!");
          child.KillChild("Child process exited.");
          break;
        } else {
          // The machine is shutting down. We just keep going until we get
          // the service_stop_event.
          continue;
        }
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
  WindowsControllerConfig global_config;

  // Parse the configuration and set the global object.
  if (global_config.ParseConfiguration() == ERROR_SUCCESS) {
    kNannyConfig = &global_config;
  } else {
    printf("Unable to parse command line.\n");
    return -1;
  }

  if (lstrcmpi(global_config.action, TEXT("install")) == 0) {
    return InstallService() ? 0 : -1;
  }

  // This table contains all the services provided by this binary.
  SERVICE_TABLE_ENTRY kDispatchTable[] = {
    { kNannyConfig->service_name,
      reinterpret_cast<LPSERVICE_MAIN_FUNCTION>(ServiceMain) },
    { NULL, NULL }
  };

  // This call returns when the service has stopped.
  // The process should simply terminate when the call returns.
  if (!StartServiceCtrlDispatcher(kDispatchTable)) {
    WindowsEventLogger("StartServiceCtrlDispatcher");
  }
  return 0;
}

}  // namespace grr

// Main entry point when built as a windows application.
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                   char *lpCmdLine, int nCmdShow) {
  return grr::real_main(__argc, __argv);
}

// Main entry point when build as a console application.
int _tmain(int argc, char *argv[]) {
  return grr::real_main(argc, argv);
}
