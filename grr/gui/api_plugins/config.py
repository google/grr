#!/usr/bin/env python
"""API handlers for accessing config."""

from grr.gui import api_call_handler_base
from grr.gui import api_call_handler_utils

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Settings"

# TODO(user): sensitivity of config options and sections should
# probably be defined together with the options themselves. Keeping
# the list of redacted options and settings here may lead to scenario
# when new sensitive option is added, but these lists are not updated.
REDACTED_OPTIONS = ["AdminUI.django_secret_key", "Mysql.database_password",
                    "Worker.smtp_password"]
REDACTED_SECTIONS = ["PrivateKeys", "Users"]


class ApiConfigOption(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiConfigOption

  def GetValueClass(self):
    return rdfvalue.RDFValue.classes.get(self.type)

  def InitFromConfigOption(self, name):
    self.name = name

    for section in REDACTED_SECTIONS:
      if name.lower().startswith(section.lower() + "."):
        self.is_redacted = True
        return self

    for option in REDACTED_OPTIONS:
      if name.lower() == option.lower():
        self.is_redacted = True
        return self

    try:
      config_value = config_lib.CONFIG.Get(name)
    except (config_lib.Error, type_info.TypeValueError):
      self.is_invalid = True
      return self

    if config_value is not None:
      # TODO(user): this is a bit of a hack as we're reusing the logic
      # from ApiDataObjectKeyValuePair. We should probably abstract this
      # away into a separate function, so that we don't have to create
      # an ApiDataObjectKeyValuePair object.
      kv_pair = api_call_handler_utils.ApiDataObjectKeyValuePair()
      kv_pair.InitFromKeyValue(name, config_value)

      self.is_invalid = kv_pair.invalid
      if not self.is_invalid:
        self.type = kv_pair.type
        self.value = kv_pair.value

    return self


class ApiConfigSection(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiConfigSection


class ApiGetConfigResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetConfigResult


class ApiGetConfigHandler(api_call_handler_base.ApiCallHandler):
  """Renders GRR's server configuration."""

  category = CATEGORY
  result_type = ApiGetConfigResult

  def _ListParametersInSection(self, section):
    for descriptor in sorted(config_lib.CONFIG.type_infos,
                             key=lambda x: x.name):
      if descriptor.section == section:
        yield descriptor.name

  def Handle(self, unused_args, token=None):
    """Build the data structure representing the config."""

    sections = {}
    for descriptor in config_lib.CONFIG.type_infos:
      if descriptor.section in sections:
        continue

      section_data = {}
      for parameter in self._ListParametersInSection(descriptor.section):
        section_data[parameter] = ApiConfigOption().InitFromConfigOption(
            parameter)

      sections[descriptor.section] = section_data

    result = ApiGetConfigResult()
    for section_name in sorted(sections):
      section = sections[section_name]

      api_section = ApiConfigSection(name=section_name)
      api_section.options = []
      for param_name in sorted(section):
        api_section.options.append(section[param_name])
      result.sections.append(api_section)

    return result


class ApiGetConfigOptionArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetConfigOptionArgs


class ApiGetConfigOptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders single option from a GRR server's configuration."""

  category = CATEGORY
  args_type = ApiGetConfigOptionArgs
  result_type = ApiConfigOption

  def Handle(self, args, token=None):
    """Renders specified config option."""

    if not args.name:
      raise ValueError("Name not specified.")

    return ApiConfigOption().InitFromConfigOption(args.name)
