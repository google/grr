#!/usr/bin/env python
"""Execute a Rekall plugin on the client memory.

This module implements the Rekall enabled client actions.
"""



import json
import os


# Initialize the Rekall plugins, so pylint: disable=unused-import
from rekall import addrspace
from rekall import constants
from rekall import io_manager
from rekall import obj
from rekall import plugins
from rekall import session
from rekall.plugins.addrspaces import standard
from rekall.ui import json_renderer
# pylint: enable=unused-import

import logging
from grr.client import actions
from grr.client import vfs
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils


class Error(Exception):
  pass


class ProfileNotFoundError(ValueError):
  pass


class GrrRenderer(json_renderer.JsonRenderer):
  """This renderer sends all messages to the server encoded as JSON."""

  # Maximum number of statements to queue before sending a reply.
  RESPONSE_CHUNK_SIZE = 1000

  def __init__(self, rekall_session=None, action=None):
    """Collect Rekall rendering commands and send to the server.

    Args:
      rekall_session: The Rekall session object.
      action: The GRR Client Action which owns this renderer. We will use it to
         actually send messages back to the server.
    """
    super(GrrRenderer, self).__init__(session=rekall_session)

    # A handle to the client action we can use for sending responses.
    self.action = action

    # The current plugin we are running.
    self.plugin = None

  def start(self, plugin_name=None):
    super(GrrRenderer, self).start(plugin_name=plugin_name)
    self.plugin = plugin_name

    return self

  def write_data_stream(self):
    """Prepares a RekallResponse and send to the server."""
    if self.data:
      response_msg = rdfvalue.RekallResponse(
          json_messages=json.dumps(self.data, separators=(",", ":")),
          plugin=self.plugin)

      # Queue the response to the server.
      self.action.SendReply(response_msg)

  def SendMessage(self, statement):
    super(GrrRenderer, self).SendMessage(statement)

    if len(self.data) > self.RESPONSE_CHUNK_SIZE:
      self.flush()


class GrrRekallSession(session.Session):
  """A GRR Specific Rekall session."""

  def __init__(self, fhandle=None, action=None, **session_args):
    super(GrrRekallSession, self).__init__(**session_args)
    self.action = action

    # Ensure the action's Progress() method is called when Rekall reports
    # progress.
    self.progress.Register(id(self), lambda *_, **__: self.action.Progress())

  def LoadProfile(self, filename):
    """Wraps the Rekall profile's LoadProfile to fetch profiles from GRR."""
    # If the user specified a special profile path we use their choice.
    try:
      return super(GrrRekallSession, self).LoadProfile(filename)
    except ValueError:
      logging.debug("Asking server for profile %s" % filename)

      # Cant load the profile, we need to ask the server for it.
      self.action.SendReply(
          rdfvalue.RekallResponse(
              missing_profile="%s/%s" % (
                  constants.PROFILE_REPOSITORY_VERSION, filename)))

      # Wait for the server to wake us up. When we wake up the server should
      # have sent the profile over by calling the WriteRekallProfile.
      self.action.Suspend()

      # Now the server should have sent the data already. We try to load the
      # profile one more time, or we die.
      return super(GrrRekallSession, self).LoadProfile(
          filename, use_cache=False)


class WriteRekallProfile(actions.ActionPlugin):
  """A client action to write a Rekall profile to the local cache."""

  in_rdfvalue = rdfvalue.RekallProfile

  def Run(self, args):
    output_filename = utils.JoinPath(
        config_lib.CONFIG["Client.rekall_profile_cache_path"], args.name)

    try:
      os.makedirs(os.path.dirname(output_filename))
    except OSError:
      pass

    with open(output_filename, "wb") as fd:
      fd.write(args.data)


class RekallAction(actions.SuspendableAction):
  """Runs a Rekall command on live memory."""
  in_rdfvalue = rdfvalue.RekallRequest
  out_rdfvalue = rdfvalue.RekallResponse

  def Iterate(self):
    """Run a Rekall plugin and return the result."""
    # Open the device pathspec as requested by the server.
    with vfs.VFSOpen(self.request.device) as fhandle:

      # Create a session and run all the plugins with it.
      session_args = self.request.session.ToDict()

      # If the user has not specified a special profile path, we use the local
      # cache directory.
      if "profile_path" not in session_args:
        session_args["profile_path"] = [config_lib.CONFIG[
            "Client.rekall_profile_cache_path"]]

      rekal_session = GrrRekallSession(action=self, **session_args)

      # Wrap GRR's VFS handler for the device in a Rekall FDAddressSpace so we
      # can pass it directly to the Rekall session as the physical address
      # space. This avoids the AS voting mechanism for Rekall's image format
      # detection.
      with rekal_session:
        rekal_session.physical_address_space = standard.FDAddressSpace(
            session=rekal_session, fhandle=fhandle)

        # Autodetect the profile. Valid plugins for this profile will become
        # available now.
        rekal_session.GetParameter("profile")

      # We will use this renderer to push results to the server.
      ui_renderer = GrrRenderer(rekall_session=rekal_session, action=self)

      for plugin_request in self.request.plugins:
        # Get the keyword args to this plugin.
        plugin_args = plugin_request.args.ToDict()
        try:
          rekal_session.RunPlugin(plugin_request.plugin,
                                  renderer=ui_renderer, **plugin_args)

        except Exception:  # pylint: disable=broad-except
          # Just ignore errors, and run the next plugin. Errors will be reported
          # through the renderer.
          pass
