// Copyright 2012 Google Inc
// All Rights Reserved.
//
//
#include "grr/client/nanny/child_controller.h"

#include <algorithm>

namespace grr {

// -----------------------------------------------------------------
// ChildProcess
// -----------------------------------------------------------------
ChildProcess::ChildProcess() {}
ChildProcess::~ChildProcess() {}
EventLogger *ChildProcess::GetEventLogger() {
  return NULL;
};

// -----------------------------------------------------------------
// ChildController
// -----------------------------------------------------------------
ChildController::~ChildController() {}

ChildController::ChildController(const struct ControllerConfig config)
    : config_(config),
      child_(),
      last_heartbeat_time_(0),
      child_is_running_(0) {}

ChildController::ChildController(const struct ControllerConfig config,
                                 ChildProcess *child)
    : config_(config),
      child_(child),
      last_heartbeat_time_(0),
      child_is_running_(0) {}


void ChildController::KillChild() {
  child_->KillChild();
};


// The main controller loop. Will be called periodically by the nanny.
void ChildController::Run() {
  time_t now = child_->GetCurrentTime();

  // Check the heartbeat from the child.
  time_t heartbeat = std::max(child_->GetHeartBeat(), last_heartbeat_time_);
  last_heartbeat_time_ = heartbeat;

  if (child_is_running_) {
    if (now - heartbeat > config_.unresponsive_kill_period) {
      // We have not received a heartbeat in a while, kill the child.
      child_->KillChild();
      child_is_running_ = 0;
    }
  } else if (heartbeat + config_.unresponsive_kill_period +
             config_.resurrection_period <= now) {
    // Make the new child.
    child_->CreateChildProcess();

    // Do not create the child again until it is time to resurrect it.
    last_heartbeat_time_ = now;
    child_is_running_ = 1;
  }
};

// -----------------------------------------------------------------


}  // namespace grr
