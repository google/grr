// Copyright 2012 Google Inc
// All Rights Reserved.

// The nanny is an external process which controls the execution of a child
// process. If the child crashes, or exits unexpectedly, the nanny will restart
// the child. If the child becomes unresponsive, the nanny will kill the child.
// The ChildController class implements the policy about when the child should
// be started and killed. Unresponsive children are killed after the
// unresponsive_kill_period and restarted after the resurrection_period.

// For example, this is the time line:

// | Child started     | Child killed             | Child started.
// ---------------------------------------------------------------->
// |<----------------->|  unresponsive_kill_period
//                     |<------------------------>| resurrection_period

// The ChildProcess class encapsulates operating system specific control of the
// child process (i.e. methods for killing and restarting the process).


#ifndef GRR_CLIENT_NANNY_CHILD_CONTROLLER_H_
#define GRR_CLIENT_NANNY_CHILD_CONTROLLER_H_

#include <ctime>
#include "grr_response_client/nanny/event_logger.h"

#ifdef WIN32
#define DISALLOW_COPY_AND_ASSIGN(TypeName)   \
  TypeName(const TypeName&);                 \
  void operator=(const TypeName&)
#else
#include "base/macros.h"                // for DISALLOW_COPY_AND_ASSIGN
#endif

namespace grr {

// A configuration object which carries information used by the child
// controller.
struct ControllerConfig {
  // Number of seconds the child must remain dead.
  int resurrection_period;

  // The maximum number of seconds since the last child heartbeat. The child
  // will be killed if this is reached.
  int unresponsive_kill_period;

  // The time we give the client on first startup to start heartbeating.
  int unresponsive_grace_period;

  // Identical messages are suppressed in the event log for this many seconds.
  int event_log_message_suppression;

  // TODO(user): Implement fail over to older child binaries. This is useful
  // during client upgrade where there is a possibility that the child is faulty
  // and fails to start. We should maintain several known good versions of the
  // child binary and revert to a previous one after successive launch failures.

  // Number of failures until the child is considered broken, and the last known
  // good version is used.
  int failure_count_to_revert;

  // Hard memory limit for clients.
  unsigned int client_memory_limit;
};

// This class represents the child process, and how to manage it. Concrete
// implementations are platform specific.
class ChildProcess {
 public:
  ChildProcess();
  virtual ~ChildProcess();

  // Kills the child unconditionally.
  virtual void KillChild(const std::string &msg) = 0;

  // Creates the child process. Returns true on success, false on failure
  // (e.g. the child executable is not found).
  virtual bool CreateChildProcess() = 0;

  // Checks the last heart beat from the child. Returns the time of the last
  // child heartbeat (Seconds since the Epoch). A value of 0 means the child
  // failed to read its heartbeat.
  virtual time_t GetHeartbeat() = 0;

  // Sets the heartbeat to a specific value.
  virtual void SetHeartbeat(unsigned int value) = 0;

  // Sets the heartbeat to the current time.
  virtual void Heartbeat() = 0;

  // Clears the last heartbeat time.
  virtual void ClearHeartbeat() = 0;

  // Gets the current time in seconds since the Epoch.
  virtual time_t GetCurrentTime() = 0;

  virtual EventLogger *GetEventLogger();

  // Returns if the spawned process is still alive.
  virtual bool IsAlive() = 0;

  // Returns if a process has been spawned.
  virtual bool Started() = 0;

  // Returns the child's memory usage.
  virtual size_t GetMemoryUsage() = 0;

  // Sets the nanny message.
  virtual void SetNannyMessage(const std::string &msg) = 0;

  // Sets a nanny message to be sent with a delay.
  virtual void SetPendingNannyMessage(const std::string &msg) = 0;

  // Sets the nanny status.
  virtual void SetNannyStatus(const std::string &msg) = 0;

  // Just sleeps for the indicated time.
  virtual void ChildSleep(unsigned int milliseconds) = 0;

 private:
  DISALLOW_COPY_AND_ASSIGN(ChildProcess);
};

// This base class implements the policies, and derived classes implement the
// operating system specific actions.
class ChildController {
 public:
  // This is the usual way to instantiate the ChildController. A new
  // ChildProcess is created.
  explicit ChildController(const struct ControllerConfig config);

  // This constructor is mainly called from tests, where the ChildProcess is
  // injected. In this case the controller takes ownership of the child.
  ChildController(const struct ControllerConfig config, ChildProcess *child);
  virtual ~ChildController();

  // Kills the child unconditionally.
  virtual void KillChild(const std::string &msg);

  // The controller's main loop.  This method should be called periodically to
  // check on the child's heartbeat status. Currently the child controller is
  // not thread-safe and so this method should always be called in the same
  // thread. After each invocation of Run(), the next call should follow not
  // more than the return value in seconds later.
  virtual time_t Run();

 private:
  struct ControllerConfig config_;

  // The child process abstraction we manage the child with.
  ChildProcess *child_;

  // The last time we know the service ran. This is required if we can not read
  // the heartbeat from the child for some reason.
  time_t last_heartbeat_time_;

  DISALLOW_COPY_AND_ASSIGN(ChildController);
};


}  // namespace grr
#endif  // GRR_CLIENT_NANNY_CHILD_CONTROLLER_H_
