#!/usr/bin/env python
"""The Dummy client action."""

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import dummy as rdf_dummy


class Dummy(actions.ActionPlugin):
  """Returns the received string."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]

  def Run(self, args: rdf_dummy.DummyRequest) -> None:
    """Returns received input back to the server, but in Windows."""

    if not args.action_input:
      raise RuntimeError("WIN args.action_input is empty, cannot proceed!")

    self.SendReply(
        rdf_dummy.DummyResult(
            action_output=f"WIN args.action_input: '{args.action_input}'"
        )
    )
