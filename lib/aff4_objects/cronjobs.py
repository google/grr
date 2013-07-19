#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.

"""These aff4 objects are periodic cron jobs."""
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue


class CronJob(aff4.AFF4Volume):
  """AFF4 object corresponding to cron jobs."""

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Schema for CronJob AFF4 object."""
    DESCRIPTION = aff4.Attribute(
        "aff4:cron/description", rdfvalue.RDFString,
        "Descripition of a cron job.", "description")

    FLOW_NAME = aff4.Attribute("aff4:cron/flow_name", rdfvalue.RDFString,
                               "This cron jobs' flow name.")

    FLOW_ARGS = aff4.Attribute("aff4:cron/flow_args", rdfvalue.Dict,
                               "This cron jobs' flow arguments.")

    FREQUENCY = aff4.Attribute(
        "aff4:cron/frequency", rdfvalue.Duration,
        "How often the cron job should be run in hours (best effort).")

    ALLOW_OVERRUNS = aff4.Attribute(
        "aff4:cron/allow_overruns", rdfvalue.RDFInteger,
        "If True, prevent the job from running again when previous run hasn't "
        "finished.")

    DISABLED = aff4.Attribute(
        "aff4:cron/disabled", rdfvalue.RDFBool,
        "If True, don't run this job.")

    CURRENT_FLOW_URN = aff4.Attribute(
        "aff4:cron/current_flow_urn", rdfvalue.RDFURN,
        "URN of the currently running flow corresponding to this cron job.",
        versioned=False, lock_protected=True)

    LAST_RUN_TIME = aff4.Attribute(
        "aff4:cron/last_run", rdfvalue.RDFDatetime,
        "The last time this cron job ran.", "last_run",
        versioned=False, lock_protected=True)

  def IsRunning(self):
    """Returns True if there's a currently running iteration of this job."""
    return self.Get(self.Schema.CURRENT_FLOW_URN) is not None

  def DueToRun(self):
    """Called periodically by the cron daemon, if True Run() will be called.

    Returns:
        True if it is time to run based on the specified frequency.
    """
    if self.Get(self.Schema.DISABLED):
      return False

    frequency = self.Get(self.Schema.FREQUENCY)
    last_run_time = self.Get(self.Schema.LAST_RUN_TIME)
    now = rdfvalue.RDFDatetime().Now()

    if (last_run_time is None or
        now.AsSecondsFromEpoch() - frequency.seconds >
        last_run_time.AsSecondsFromEpoch()):

      return (self.Get(self.Schema.ALLOW_OVERRUNS) or
              self.Get(self.Schema.CURRENT_FLOW_URN) is None)
    else:
      return False

  def Run(self, force=False):
    """Do the actual work of the Cron. Will first check if DueToRun is True.

    CronJob object must be locked (i.e. opened via OpenWithLock) for Run() to be
    called.

    Args:
      force: If True, the job will run no matter what (i.e. even if DueToRun()
             returns False).

    Raises:
      LockError: if the object is not locked.
    """
    if not self.locked:
      raise aff4.LockError("CronJob must be locked for Run() to be called.")

    # If currently running flow has finished, update our state.
    current_flow_urn = self.Get(self.Schema.CURRENT_FLOW_URN)
    if current_flow_urn:
      current_flow = aff4.FACTORY.Open(current_flow_urn, token=self.token)
      if not current_flow.IsRunning():
        self.DeleteAttribute(self.Schema.CURRENT_FLOW_URN)
        self.Flush()

    if not force and not self.DueToRun():
      return

    # These flows are not started with a client id, hence they can not
    # CallClient().
    flow_urn = flow.GRRFlow.StartFlow(
        None, str(self.Get(self.Schema.FLOW_NAME)), token=self.token,
        **self.Get(self.Schema.FLOW_ARGS).ToDict())

    # TODO(user): get rid of it when everything is RDFURN.
    flow_urn = rdfvalue.RDFURN(flow_urn)

    self.Set(self.Schema.CURRENT_FLOW_URN, flow_urn)
    self.Set(self.Schema.LAST_RUN_TIME, rdfvalue.RDFDatetime().Now())
    self.Flush()

    flow_link = aff4.FACTORY.Create(self.urn.Add(flow_urn.Basename()),
                                    "AFF4Symlink", token=self.token)
    flow_link.Set(flow_link.Schema.SYMLINK_TARGET(flow_urn))
    flow_link.Close()
