// Copyright 2012 Google Inc
// All Rights Reserved.
//
//
#include "grr_response_client/nanny/child_controller.h"

#include <algorithm>

namespace grr {

// -----------------------------------------------------------------
// ChildProcess
// -----------------------------------------------------------------
ChildProcess::ChildProcess() {}
ChildProcess::~ChildProcess() {}
EventLogger *ChildProcess::GetEventLogger() {
  return NULL;
}

// -----------------------------------------------------------------
// ChildController
// -----------------------------------------------------------------
ChildController::~ChildController() {}

ChildController::ChildController(const struct ControllerConfig config)
    : config_(config),
      child_(),
      last_heartbeat_time_(0) {}

ChildController::ChildController(const struct ControllerConfig config,
                                 ChildProcess *child)
    : config_(config),
      child_(child),
      last_heartbeat_time_(0) {}


void ChildController::KillChild(const std::string &msg) {
  child_->KillChild(msg);
}


// The main controller loop. Will be called periodically by the nanny.
time_t ChildController::Run() {
  time_t now = child_->GetCurrentTime();

  // Check the heartbeat from the child.
  time_t heartbeat = std::max(child_->GetHeartbeat(), last_heartbeat_time_);
  if (heartbeat == 0) {
    return 1;
  }
  last_heartbeat_time_ = heartbeat;

  time_t call_delay = 0;
  if (child_->Started() && child_->IsAlive()) {
    call_delay = config_.unresponsive_kill_period - (now - heartbeat);
    if (now - heartbeat > config_.unresponsive_kill_period) {
      // There is a very unlikely race condition if the machine gets suspended
      // for longer than unresponsive_kill_period seconds so we give the client
      // some time to catch up.
      child_->ChildSleep(2000);
      heartbeat = std::max(child_->GetHeartbeat(), last_heartbeat_time_);
      if (now - heartbeat > config_.unresponsive_kill_period) {
        const std::string msg("No heartbeat received.");
        // We have not received a heartbeat in a while, kill the child.
        child_->SetNannyMessage(msg);
        child_->KillChild(msg);
        call_delay = 1;
      }
    }
  } else {
    if (heartbeat + config_.unresponsive_kill_period +
        config_.resurrection_period <= now) {
      // Make the new child.
      child_->CreateChildProcess();

      // Do not create the child again until it is time to resurrect it.
      last_heartbeat_time_ = now;
      call_delay = 1;
    } else {
      call_delay = heartbeat + config_.unresponsive_kill_period +
          config_.resurrection_period - now;
    }
  }
  return call_delay;
}

// -----------------------------------------------------------------


}  // namespace grr
