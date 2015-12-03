#!/usr/bin/env python
"""API handlers for accessing config."""

from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import config_lib
from grr.lib import type_info

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Settings"

REDACTED_OPTIONS = ["AdminUI.django_secret_key", "Mysql.database_password",
                    "Worker.smtp_password"]
REDACTED_SECTIONS = ["PrivateKeys", "Users"]


def RenderConfigOption(name):
  """Renders config option with a given name."""

  option_value = config_lib.CONFIG.Get(name)
  raw_value = config_lib.CONFIG.GetRaw(name)

  # TODO(user): implement proper is_default detection.
  is_default = False
  # TODO(user): implement proper interpolation detection.
  is_expanded = False

  if isinstance(option_value, str):
    raw_value = option_value = None
    value_type = "binary"
  else:
    value_type = "plain"
    option_value = api_value_renderers.RenderValue(option_value)

  return dict(raw_value=raw_value,
              value=option_value,
              is_expanded=is_expanded,
              is_default=is_default,
              type=value_type)


class ApiGetConfigHandler(api_call_handler_base.ApiCallHandler):
  """Renders GRR's server configuration."""

  category = CATEGORY

  def _IsBadSection(self, section):
    for bad_section in REDACTED_SECTIONS:
      if section.lower().startswith(bad_section.lower()):
        return True

  def _ListParametersInSection(self, section):
    for descriptor in sorted(config_lib.CONFIG.type_infos,
                             key=lambda x: x.name):
      if descriptor.section == section:
        yield descriptor.name

  def Render(self, unused_args, token=None):
    """Build the data structure representing the config."""

    sections = {}
    for descriptor in config_lib.CONFIG.type_infos:
      if descriptor.section in sections:
        continue

      is_bad_section = self._IsBadSection(descriptor.section)

      section_data = {}

      for parameter in self._ListParametersInSection(descriptor.section):
        try:
          if parameter in REDACTED_OPTIONS or is_bad_section:
            parameter_data = {"type": "redacted"}
          else:
            parameter_data = RenderConfigOption(parameter)

        except (config_lib.Error, type_info.TypeValueError) as e:
          parameter_data = {"type": "error",
                            "error_message": str(e)}

        section_data[parameter] = parameter_data

      sections[descriptor.section] = section_data

    return sections


class ApiGetConfigOptionArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetConfigOptionArgs


class ApiGetConfigOptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders single option from a GRR server's configuration."""

  category = CATEGORY
  args_type = ApiGetConfigOptionArgs

  def Render(self, args, token=None):
    """Renders specified config option."""

    if not args.name:
      raise ValueError("Name not specified.")

    redacted = False

    for section in REDACTED_SECTIONS:
      if args.name.startswith(section + "."):
        redacted = True
        break

    for option in REDACTED_OPTIONS:
      if args.name == option:
        redacted = True
        break

    if redacted:
      return dict(status="OK",
                  type="redacted")
    else:
      rendered_option = RenderConfigOption(args.name)
      return dict(status="OK",
                  **rendered_option)
