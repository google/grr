#!/usr/bin/env python
"""Execute a Rekall plugin on the client memory.

This module implements the Rekall enabled client actions.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import pdb
import sys
import traceback


from future.utils import iteritems
import psutil

# Initialize the Rekall plugins, so pylint: disable=unused-import
from grr_response_client.components.rekall_support import fix_deps
from rekall import addrspace
from rekall import config as rekall_config
from rekall import constants
from rekall import io_manager
from rekall import obj
from rekall import plugins
from rekall import session
from rekall.plugins.addrspaces import standard
from rekall.plugins.renderers import data_export
from rekall.plugins.tools import caching_url_manager
from rekall.ui import json_renderer
# pylint: enable=unused-import

from grr_response_client import actions
from grr_response_client.client_actions import tempfiles
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types


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
        renderer=self.renderer, session=self.session)

  def EncodeToJsonSafe(self, item, **options):
    object_renderer = self.ForTarget(item, "DataExportRenderer")
    return object_renderer(
        renderer=self.renderer, session=self.session).EncodeToJsonSafe(
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
    return super(GRRRekallRenderer, self).start(
        plugin_name=plugin_name, kwargs=kwargs)

  def write_data_stream(self):
    """Prepares a RekallResponse and send to the server."""
    if self.data:

      response_msg = rdf_rekall_types.RekallResponse(
          json_messages=self.robust_encoder.encode(self.data),
          json_context_messages=self.robust_encoder.encode(
              list(iteritems(self.context_messages))),
          plugin=self.plugin)

      self.context_messages = self.new_context_messages
      self.new_context_messages = {}

      # Queue the response to the server.
      self.action.SendReply(response_msg)

  def SendMessage(self, statement):
    super(GRRRekallRenderer, self).SendMessage(statement)
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

  def __init__(self,
               fhandle=None,
               action=None,
               initial_profiles=None,
               **session_args):
    super(GrrRekallSession, self).__init__(
        cache_dir=config.CONFIG["Client.rekall_profile_cache_path"])

    self.action = action

    # Just hard code the initial repository manager. Note this can be
    # overwritten later if needed.
    self._repository_managers = [(None,
                                  RekallCachingIOManager(
                                      initial_profiles=initial_profiles,
                                      session=self))]

    # Apply default configuration options to the session state, unless
    # explicitly overridden by the session_args.
    with self.state:
      for k, v in iteritems(session_args):
        self.state.Set(k, v)

      for name, options in iteritems(rekall_config.OPTIONS.args):
        # We don't want to override configuration options passed via
        # **session_args.
        if name not in session_args:
          self.state.Set(name, options.get("default"))

    # Ensure the action's Progress() method is called when Rekall reports
    # progress.
    self.proc = psutil.Process()
    self.memory_quota = config.CONFIG["Client.rss_max"] * 1024 * 1024
    self.progress.Register(id(self), lambda *_, **__: self._CheckQuota())

  def _CheckQuota(self):
    """Ensures we do not exceed the allowed memory limit."""
    # Check the memory use is not exceeded.
    if self.proc.memory_info().rss > self.memory_quota:
      raise MemoryError("Exceeded memory quota")

    # Ensure the action progress is reported so we do not get killed.
    self.action.Progress()

  def GetRenderer(self, **kwargs):
    # Reuse the same renderer on recursive GetRenderer() calls.
    if self.renderers:
      return self.renderers[-1]

    # We will use this renderer to push results to the server.
    result = GRRRekallRenderer(
        rekall_session=self, action=self.action, **kwargs)
    self.renderers.append(result)

    return result


class RekallIOManager(io_manager.IOManager):
  """An IO manager to talk with the GRR server."""

  def GetData(self, name, raw=False, default=None):
    # Cant load the profile, we need to ask the server for it.
    self.session.logging.info("Asking server for profile %s", name)
    profile = self.session.action.grr_worker.GetRekallProfile(
        name, version=constants.PROFILE_REPOSITORY_VERSION)

    if not profile:
      return obj.NoneObject()

    return self.Decoder(profile.payload)

  def SetInventory(self, inventory):
    self._inventory = inventory


class RekallCachingIOManager(caching_url_manager.CachingManager):
  DELEGATE = RekallIOManager

  def __init__(self, initial_profiles, **kwargs):
    self.initial_profiles = initial_profiles
    super(RekallCachingIOManager, self).__init__(**kwargs)

  def CheckUpstreamRepository(self):
    for profile in (self.initial_profiles or []):
      # Copy the inventory to the remote IO manager.
      if profile.name == "inventory":
        self.url_manager.SetInventory(self.Decoder(profile.payload))

      else:
        # Everything else, save locally to the cache.
        self.StoreData(profile.name, self.Decoder(profile.payload))

    super(RekallCachingIOManager, self).CheckUpstreamRepository()


class RekallAction(actions.ActionPlugin):
  """Runs a Rekall command on live memory."""
  in_rdfvalue = rdf_rekall_types.RekallRequest
  out_rdfvalues = [rdf_rekall_types.RekallResponse]

  def Run(self, args):
    """Run a Rekall plugin and return the result."""
    # Create a session and run all the plugins with it.
    session_args = args.session.ToDict()

    if "filename" not in session_args and args.device:
      session_args["filename"] = args.device.path

    rekal_session = GrrRekallSession(
        action=self, initial_profiles=args.profiles, **session_args)

    plugin_errors = []

    for plugin_request in args.plugins:
      # Get the keyword args to this plugin.
      plugin_args = plugin_request.args.ToDict()
      try:
        rekal_session.RunPlugin(plugin_request.plugin, **plugin_args)
      except Exception:  # pylint: disable=broad-except
        tb = traceback.format_exc()
        logging.error("While running plugin (%s): %s", plugin_request.plugin,
                      tb)
        plugin_errors.append(tb)
      finally:
        rekal_session.Flush()

    if plugin_errors:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                     u"\n\n".join(plugin_errors))
    # Rekall uses quite a bit of memory so we force a garbage collection here
    # even though it may cost a second or two of cpu time.
    self.Progress()
    self.ForceGC()
