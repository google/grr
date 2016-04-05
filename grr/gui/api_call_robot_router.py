#!/usr/bin/env python
"""Implementation of a router class that should be used by robot users."""



from grr.gui import api_call_router
from grr.gui import api_call_router_without_checks


class ApiCallRobotRouter(api_call_router.ApiCallRouter):
  """Restricted router to be used by robots."""

  def __init__(self, delegate=None):
    super(ApiCallRobotRouter, self).__init__()

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  # Robot methods (methods that provide limited access to the system and
  # are supposed to be triggered by the scripts).
  # ====================================================================
  #
  def StartGetFileOperation(self, args, token=None):
    return self.delegate.StartGetFileOperation(args, token=token)

  def GetFlowStatus(self, args, token=None):
    return self.delegate.GetFlowStatus(args, token=token)
