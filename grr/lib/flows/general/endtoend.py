#!/usr/bin/env python
"""Flow to run endtoend tests in production."""

import traceback

from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import flow
from grr.lib import registry
from grr.lib import stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2
from grr.proto import jobs_pb2


class EndToEndTestFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.EndToEndTestFlowArgs


class EndToEndTestResult(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.EndToEndTestResult


class EndToEndTestFlow(flow.GRRFlow):
  """Run end-to-end tests on a client.

  If no test names are specified we run all tests that inherit from
  endtoend_tests.base.AutomatedTest. We report back results for each test, but
  always exit normally.  i.e. we don't raise if we get test failures, since this
  enables results to be collected normally in the hunt that runs this flow from
  a cronjob.
  """
  category = "/Administrative/"
  args_type = EndToEndTestFlowArgs
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

  def RunTest(self, cls):
    """Run the test flow."""
    test_object = cls(client_id=self.client_id,
                      platform=self.state.client_summary.system_info.system,
                      token=self.token,
                      local_worker=False)

    self.Log("Running %s on %s (%s: %s, %s, %s)",
             test_object.__class__.__name__, self.client_id,
             self.state.client_summary.system_info.fqdn,
             self.state.client_summary.system_info.system,
             self.state.client_summary.system_info.version,
             self.state.client_summary.system_info.machine)

    # If setUp fails it will kill the whole flow.  This is intentional and
    # mimics the python test runner.  Generally setUp and tearDown should be
    # safe.
    test_object.setUp()

    # We need to set write_intermediate_results=True here so that the results
    # are written to the collections belonging to the child flows. The default
    # behaviour is to only write to the top level parent collection, which in
    # this case is us.  There are a bunch of tests that check for empty
    # collections and fail in this case.

    # Since CallFlow runs Start, a flow under test that raises in its Start
    # method will kill the EndToEndTest run.  Protecting and reporting on this
    # significantly complicates this code, and a flow raising in Start is really
    # broken, so we allow this behaviour.
    test_object.session_id = self.CallFlow(test_object.flow,
                                           next_state="ProcessResults",
                                           write_intermediate_results=True,
                                           **test_object.args)

    # Save the object so we can call CheckFlow once the flow is done
    self.state.flow_test_map[test_object.session_id] = test_object

  def _AddTest(self, cls, system, client_version):
    if aff4.issubclass(cls, base.AutomatedTest):
      if system not in cls.platforms:
        return
      if cls.client_min_version and client_version < cls.client_min_version:
        return
      if not cls.__name__.startswith("Abstract"):
        self.state.test_set.add(cls)

  @flow.StateHandler(next_state="RunFirstTest")
  def Start(self):
    self.state.Register("test_set", set())
    self.state.Register("flow_test_map", {})
    self.state.Register("client_summary", None)
    self.state.Register("pass_count", 0)
    self.state.Register("fail_count", 0)

    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.client_summary = self.client.GetSummary()
    system = self.state.client_summary.system_info.system
    client_version = self.state.client_summary.client_info.client_version

    for test_name in self.args.test_names:
      self._AddTest(base.AutomatedTest.classes[test_name], system,
                    client_version)

    # If no tests were specified, get all the AutomatedTest classes.
    if not self.args.test_names:
      for cls in base.AutomatedTest.classes.values():
        self._AddTest(cls, system, client_version)

    if not self.state.test_set:
      raise flow.FlowError("No applicable tests for client: %s" %
                           self.state.client_summary)

    # Get out of the start method before we run any tests
    self.CallState(next_state="RunFirstTest")

  @flow.StateHandler(next_state="ProcessResults")
  def RunFirstTest(self, unused_responses):
    self.RunTest(self.state.test_set.pop())

  @flow.StateHandler(next_state=["ProcessResults", "End"])
  def ProcessResults(self, responses):
    test_object = self.state.flow_test_map[responses.status.child_session_id]
    cls_name = test_object.__class__.__name__
    system = self.state.client_summary.system_info.system
    result = EndToEndTestResult(test_class_name=cls_name, success=False)
    try:
      test_object.CheckFlow()
      result.success = True
      stats.STATS.IncrementCounter("endtoend_test_success",
                                   fields=[cls_name, system])
    except Exception:  # pylint: disable=broad-except
      # CheckFlow verifies the test result and can raise any number of different
      # exceptions.  We want to log and move on so that we can run all tests,
      # not just die on first failure.
      self.state.fail_count += 1
      stats.STATS.IncrementCounter("endtoend_test_failure",
                                   fields=[cls_name, system])
      backtrace = traceback.format_exc()
      self.Log(backtrace)
      result.log = backtrace

    # If tearDown fails it will kill the whole flow.  This is intentional and
    # mimics the python test runner.  Generally setUp and tearDown should be
    # safe.
    test_object.tearDown()

    # Delay declaring success until tearDown completes successfully.
    if result.success:
      self.Log("%s Success" % test_object.__class__.__name__)
      self.state.pass_count += 1

    self.SendReply(result)

    # If there are still tests left, run the next one
    if self.state.test_set:
      self.RunTest(self.state.test_set.pop())

  @flow.StateHandler()
  def End(self, responses):
    """Log results."""
    self.Log("%s tests passed, %s failed.", self.state.pass_count,
             self.state.fail_count)


class EndToEndTestStatsInit(registry.InitHook):
  """Initialize EndToEndTest stats."""
  pre = ["AFF4InitHook"]

  def RunOnce(self):
    stats.STATS.RegisterCounterMetric("endtoend_test_failure",
                                      fields=[("test_name", str),
                                              ("platform", str)])
    stats.STATS.RegisterCounterMetric("endtoend_test_success",
                                      fields=[("test_name", str),
                                              ("platform", str)])
