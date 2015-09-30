#!/usr/bin/env python
"""Execute a Rekall plugin on the client memory.

This module implements the Rekall enabled client actions.
"""


import copy
import logging
import os
import pdb
import sys
import traceback


# Initialize the Rekall plugins, so pylint: disable=unused-import
from rekall import addrspace
from rekall import config
from rekall import constants
from rekall import io_manager
from rekall import obj
from rekall import plugins
from rekall import session
from rekall.plugins.addrspaces import standard
from rekall.plugins.renderers import data_export
from rekall.ui import json_renderer
# pylint: enable=unused-import

import logging
from grr.client import actions
from grr.client import vfs
from grr.client.client_actions import tempfiles
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import rekall_types


class Error(Exception):
  pass


class ProfileNotFoundError(ValueError):
  pass


class GRRObjectRenderer(data_export.NativeDataExportObjectRenderer):
  """A default object renderer for the GRRRekallRenderer.

  GRR Renders all Rekall objects using the Rekall DataExportRenderer. By default
  we just delegate everything to DataExportRenderer.
  """
  renders_type = "object"
  renderers = ["GRRRekallRenderer"]

  def _GetDelegateObjectRenderer(self, item):
    return self.FromEncoded(item, "DataExportRenderer")(
        renderer=self.renderer)

  def EncodeToJsonSafe(self, item, **options):
    object_renderer = self.ForTarget(item, "DataExportRenderer")
    return object_renderer(renderer=self.renderer).EncodeToJsonSafe(
        item, **options)

  def DecodeFromJsonSafe(self, value, options):
    return self._GetDelegateObjectRenderer(value).DecodeFromJsonSafe(
        value, options)

  def RawHTML(self, item, **options):
    raise NotImplementedError("Not producing HTML on the client.")

  def Summary(self, item, **options):
    return self._GetDelegateObjectRenderer(item).Summary(item, **options)


class GRRRekallRenderer(data_export.DataExportRenderer):
  """This renderer sends all messages to the server encoded as JSON.

  Note that this renderer is used to encode and deliver Rekall objects to the
  server. Additionally Rekall ObjectRenderer implementations specific to GRR
  will be attached to this renderer.
  """

  name = None

  # Maximum number of statements to queue before sending a reply.
  RESPONSE_CHUNK_SIZE = 1000

  def __init__(self, rekall_session=None, action=None, **kwargs):
    """Collect Rekall rendering commands and send to the server.

    Args:
      rekall_session: The Rekall session object.
      action: The GRR Client Action which owns this renderer. We will use it to
         actually send messages back to the server.
      **kwargs: Passthrough.
    """
    try:
      sys.stdout.isatty()
    except AttributeError:
      sys.stdout.isatty = lambda: False

    super(GRRRekallRenderer, self).__init__(session=rekall_session, **kwargs)

    # A handle to the client action we can use for sending responses.
    self.action = action

    # The current plugin we are running.
    self.plugin = None

    self.context_messages = {}
    self.new_context_messages = {}
    self.robust_encoder = json_renderer.RobustEncoder(
        logging=rekall_session.logging)

  def start(self, plugin_name=None, kwargs=None):
    self.plugin = plugin_name
    return super(GRRRekallRenderer, self).start(plugin_name=plugin_name,
                                                kwargs=kwargs)

  def write_data_stream(self):
    """Prepares a RekallResponse and send to the server."""
    if self.data:

      response_msg = rekall_types.RekallResponse(
          json_messages=self.robust_encoder.encode(self.data),
          json_context_messages=self.robust_encoder.encode(
              self.context_messages.items()),
          plugin=self.plugin)

      self.context_messages = self.new_context_messages
      self.new_context_messages = {}

      # Queue the response to the server.
      self.action.SendReply(response_msg)

  def SendMessage(self, statement):
    # Copy required temporarily until Rekall 1.4.2 integration.
    super(GRRRekallRenderer, self).SendMessage(copy.deepcopy(statement))

    if statement[0] in ["s", "t"]:
      self.new_context_messages[statement[0]] = statement[1]

    if len(self.data) > self.RESPONSE_CHUNK_SIZE:
      self.flush()

  def open(self, directory=None, filename=None, mode="rb"):
    fd, pathspec = tempfiles.CreateGRRTempFileVFS(filename=filename, mode=mode)
    self.SendMessage(["file", pathspec.ToPrimitiveDict()])
    return fd

  def report_error(self, message):
    super(GRRRekallRenderer, self).report_error(message)
    if flags.FLAGS.debug:
      pdb.post_mortem()


class GrrRekallSession(session.Session):
  """A GRR Specific Rekall session."""

  def __init__(self, fhandle=None, action=None, **session_args):
    super(GrrRekallSession, self).__init__(**session_args)
    self.action = action

    # Apply default configuration options to the session state, unless
    # explicitly overridden by the session_args.
    with self.state:
      for name, options in config.OPTIONS.args.iteritems():
        # We don't want to override configuration options passed via
        # **session_args.
        if name not in self.state:
          self.state.Set(name, options.get("default"))

    # Ensure the action's Progress() method is called when Rekall reports
    # progress.
    self.progress.Register(id(self), lambda *_, **__: self.action.Progress())

  def LoadProfile(self, name, **kw):
    """Wraps the Rekall profile's LoadProfile to fetch profiles from GRR."""
    profile = None

    # If the user specified a special profile path we use their choice.
    try:
      profile = super(GrrRekallSession, self).LoadProfile(name, **kw)
    except io_manager.IOManagerError as e:
      # Currently, Rekall will raise when the repository directory is not
      # created. This is fine, because we'll create the directory after
      # WriteRekallProfile runs a few lines later.
      self.logging.warning(e)

    if profile:
      return profile

    # Cant load the profile, we need to ask the server for it.
    self.logging.info("Asking server for profile %s", name)
    self.action.SendReply(
        rekall_types.RekallResponse(
            missing_profile=name,
            repository_version=constants.PROFILE_REPOSITORY_VERSION,
        ))

    # Wait for the server to wake us up. When we wake up the server should
    # have sent the profile over by calling the WriteRekallProfile.
    self.action.Suspend()

    # Now the server should have sent the data already. We try to load the
    # profile one more time.
    return super(GrrRekallSession, self).LoadProfile(name, use_cache=False)

  def GetRenderer(self, **kwargs):
    # We will use this renderer to push results to the server.
    return GRRRekallRenderer(rekall_session=self, action=self.action, **kwargs)

  def _HandleRunPluginException(self, ui_renderer, e):
    """Log the exception and raise it."""
    self.logging.error(str(e))
    raise e


class WriteRekallProfile(actions.ActionPlugin):
  """A client action to write a Rekall profile to the local cache."""

  in_rdfvalue = rekall_types.RekallProfile

  def Run(self, args):
    output_filename = utils.JoinPath(
        config_lib.CONFIG["Client.rekall_profile_cache_path"],
        args.version, args.name)

    try:
      os.makedirs(os.path.dirname(output_filename))
    except OSError:
      pass

    with open(output_filename + ".gz", "wb") as fd:
      fd.write(args.data)


# TODO(user): Refactor the caching functionality to use Rekall's own caching
# system.
class RekallCachingIOManager(io_manager.DirectoryIOManager):
  order = io_manager.DirectoryIOManager.order - 1

  def CheckInventory(self, name):
    path = self._GetAbsolutePathName(name)
    result = (os.access(path + ".gz", os.F_OK) or
              os.access(path, os.F_OK))

    return result


class RekallAction(actions.SuspendableAction):
  """Runs a Rekall command on live memory."""
  in_rdfvalue = rekall_types.RekallRequest
  out_rdfvalue = rekall_types.RekallResponse

  def Iterate(self):
    """Run a Rekall plugin and return the result."""
    # Create a session and run all the plugins with it.
    session_args = self.request.session.ToDict()

    if "filename" not in session_args and self.request.device:
      session_args["filename"] = self.request.device.path

    # If the user has not specified a special profile path, we use the local
    # cache directory.
    if "repository_path" not in session_args:
      session_args["repository_path"] = [config_lib.CONFIG[
          "Client.rekall_profile_cache_path"]]

    rekal_session = GrrRekallSession(action=self, **session_args)

    plugin_errors = []

    for plugin_request in self.request.plugins:
      # Get the keyword args to this plugin.
      plugin_args = plugin_request.args.ToDict()
      try:
        rekal_session.RunPlugin(plugin_request.plugin, **plugin_args)
      except Exception:  # pylint: disable=broad-except
        tb = traceback.format_exc()
        logging.error("While running plugin (%s): %s",
                      plugin_request.plugin, tb)
        plugin_errors.append(tb)

    if plugin_errors:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                     u"\n\n".join(plugin_errors))
    # Rekall uses quite a bit of memory so we force a garbage collection here
    # even though it may cost a second or two of cpu time.
    self.Progress()
    self.ForceGC()


class GetMemoryInformation(actions.ActionPlugin):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalue = rekall_types.MemoryInformation

  def Run(self, args):
    """Run."""
    # This action might crash the box so we need to flush the transaction log.
    self.SyncTransactionLog()

    if args.pathtype != "MEMORY":
      raise RuntimeError("Can only GetMemoryInformation on memory devices.")

    with vfs.VFSOpen(args) as fd:
      self.SendReply(fd.GetMemoryInformation())
