#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Execute a volatility command on the client memory.

This module implements the volatility enabled client actions which enable
volatility to operate directly on the client.
"""




# Initialize the volatility plugins, so pylint: disable=unused-import
from volatility import addrspace
from volatility import obj
from volatility import plugins
from volatility import session
from volatility.plugins.addrspaces import standard
from volatility.ui import renderer
# pylint: enable=unused-import

from grr.client import actions
from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import utils


# pylint: disable=g-bad-name
class ProtobufRenderer(renderer.RendererBaseClass):
  """This stores all the data in a protobuf."""

  class Modes(object):
    TABLE = 1
    STRING = 2

  def __init__(self, **kwargs):
    super(ProtobufRenderer, self).__init__(**kwargs)

    self.response = rdfvalue.VolatilityResult()
    self.active_section = None
    self.mode = None

  def InitSection(self, mode=None):
    if self.mode != mode and self.active_section:
      self.response.sections.Append(self.active_section)
      self.active_section = None
    if not self.active_section:
      self.active_section = rdfvalue.VolatilitySection()
    self.mode = mode

  def end(self):
    self.response.sections.Append(self.active_section)

  def start(self, plugin_name=None, kwargs=None):
    _ = kwargs
    if plugin_name:
      self.response.plugin = plugin_name

  def write(self, data):
    self.format(data)

  def format(self, formatstring, *data):
    _ = formatstring, data

    self.InitSection(self.Modes.STRING)
    active_list = self.active_section.formatted_value_list
    formatted_value = active_list.formatted_values.Append()
    formatted_value.formatstring = formatstring
    values = formatted_value.data

    for d in data:
      self.AddValue(values, d)

  def section(self):
    self.response.sections.Append(self.active_section)
    self.active_section = None

  def flush(self):
    pass

  def table_header(self, title_format_list=None, suppress_headers=False,
                   name=None):
    _ = suppress_headers, name

    self.InitSection(self.Modes.TABLE)

    for (print_name, name, format_hint) in title_format_list:
      self.active_section.table.headers.Append(print_name=print_name,
                                               name=name,
                                               format_hint=format_hint)

  def AddValue(self, row, value):
    response = row.values.Append()
    if isinstance(value, obj.BaseObject):
      response.type = value.obj_type
      response.name = value.obj_name
      response.offset = value.obj_offset
      response.vm = utils.SmartStr(value.obj_vm)

      try:
        response.value = value.__int__()
      except (AttributeError, ValueError):
        pass

      try:
        string_value = value.__unicode__()
      except (AttributeError, ValueError):
        try:
          string_value = value.__str__()
        except (AttributeError, ValueError):
          pass

      if string_value:
        try:
          int_value = int(string_value)
          # If the string converts to an int but to a different one as the int
          # representation, we send it.
          if int_value != response.value:
            response.svalue = utils.SmartUnicode(string_value)
        except ValueError:
          # We also send if it doesn't convert back to an int.
          response.svalue = utils.SmartUnicode(string_value)

    elif isinstance(value, (bool)):
      response.svalue = utils.SmartUnicode(str(value))
    elif isinstance(value, (int, long)):
      response.value = value
    elif isinstance(value, (basestring)):
      response.svalue = utils.SmartUnicode(value)
    elif isinstance(value, obj.NoneObject):
      response.type = value.__class__.__name__
      response.reason = value.reason
    else:
      response.svalue = utils.SmartUnicode(repr(value))

  def table_row(self, *args):
    """Outputs a single row of a table."""

    self.InitSection(self.Modes.TABLE)

    row = self.active_section.table.rows.Append()
    for value in args:
      self.AddValue(row, value)

  def GetResponse(self):
    return self.response

  def RenderProgress(self, *args):
    self.session.progress(*args)


class UnicodeStringIO(object):
  """Just like StringIO but uses unicode strings."""

  def __init__(self):
    self.data = u""

  # Have to stick to an interface here so pylint: disable=g-bad-name
  def write(self, data):
    self.data += utils.SmartUnicode(data)

  def getvalue(self):
    return self.data


class CachingFDAddressSpace(addrspace.CachingAddressSpaceMixIn,
                            standard.FDAddressSpace):
  """A Caching version of the address space."""


class VolatilityAction(actions.ActionPlugin):
  """Runs a volatility command on live memory."""
  in_rdfvalue = rdfvalue.VolatilityRequest
  out_rdfvalue = rdfvalue.VolatilityResult

  def Run(self, request):
    """Run a volatility plugin and return the result."""

    def Progress(message=None, **_):
      """Allow volatility to heartbeat us so we do not die."""
      _ = message
      self.Progress()

    # Create a session and run all the plugins with it.
    with vfs.VFSOpen(request.device) as fhandle:
      session_args = request.session.ToDict()
      vol_session = session.Session(**session_args)

      # Make the physical address space by wrapping our VFS handler.
      vol_session.physical_address_space = CachingFDAddressSpace(
          fhandle=fhandle)

      # Set the progress method so the nanny is heartbeat.
      vol_session.progress = Progress
      vol_session.renderer = "ProtobufRenderer"

      # Get the dtb from the driver if possible,
      # it significantly speeds up detection.
      try:
        vol_session.dtb = fhandle.cr3
      except AttributeError:
        pass

      # Get the kdbg from the driver if possible,
      # it significantly speeds up detection.
      try:
        vol_session.kdbg = fhandle.kdbg
      except AttributeError:
        pass

      # Which profile should be used?
      if request.profile:
        vol_session.profile = request.profile
      else:
        vol_session.plugins.guess_profile().update_session()

      if not vol_session.profile:
        raise RuntimeError("Unable to autodetect profile")

      # Try to load the kernel address space now.
      if not vol_session.kernel_address_space:
        vol_session.plugins.load_as().GetVirtualAddressSpace()

      # Get the keyword args to this plugin.
      vol_args = request.args.ToDict()
      for plugin, plugin_args in vol_args.items():
        error = ""

        # Heartbeat the client to ensure we keep our nanny happy.
        vol_session.progress(message="Running plugin %s" % plugin)

        ui_renderer = ProtobufRenderer(session=vol_session)
        if plugin_args is None:
          plugin_args = {}
        else:
          plugin_args = plugin_args.ToDict()

        try:
          vol_session.vol(plugin, renderer=ui_renderer, **plugin_args)
        except Exception as e:  # pylint: disable=broad-except
          error = str(e)

        response = ui_renderer.GetResponse()
        if error:
          response.error = error

        # Send it back to the server.
        self.SendReply(response)
