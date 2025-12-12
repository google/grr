#!/usr/bin/env python
"""API handlers for accessing config."""

import logging
from typing import Any, Optional

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_proto.api import config_pb2
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.models import hunts as models_hunts
# This import is needed to register RDF types used in config values which are
# otherwise not directly imported by the code.
# pylint: disable=unused-import
from grr_response_server.rdfvalues import wrappers as rdf_wrappers
# pylint: enable=unused-import


# TODO(user): sensitivity of config options and sections should
# probably be defined together with the options themselves. Keeping
# the list of redacted options and settings here may lead to scenario
# when new sensitive option is added, but these lists are not updated.
REDACTED_OPTIONS = [
    "AdminUI.django_secret_key",
    "AdminUI.csrf_secret_key",
    "Mysql.password",
    "Mysql.database_password",
    "Worker.smtp_password",
]
REDACTED_SECTIONS = ["PrivateKeys", "Users"]


def _IsSupportedValueType(value: Any) -> bool:
  """Returns whether the given config value type is supported in the UI.

  Args:
    value: value to validate.

  Returns:
    True if the value is supported in the UI, False otherwise.
  """
  if isinstance(value, float) and not value.is_integer():
    return False
  elif rdfvalue.RDFInteger.IsNumeric(value):
    return True
  elif isinstance(value, str):
    return True
  elif isinstance(value, bytes):
    return True
  elif isinstance(value, bool):
    return True
  elif isinstance(value, rdfvalue.RDFValue):
    return True
  else:
    return False


def ApiConfigOptionFromOptionName(name: str) -> config_pb2.ApiConfigOption:
  """Builds an `ApiConfigOption` from a given config option name.

  Args:
    name: name of the config option to build proto from.

  Returns:
    An `ApiConfigOption` proto with information on the given config: value
    extracted from current config, its type and whether it's redacted or
    invalid.
  """

  res = config_pb2.ApiConfigOption(name=name)

  for section in REDACTED_SECTIONS:
    if name.lower().startswith(section.lower() + "."):
      return config_pb2.ApiConfigOption(name=name, is_redacted=True)

  for option in REDACTED_OPTIONS:
    if name.lower() == option.lower():
      return config_pb2.ApiConfigOption(name=name, is_redacted=True)

  try:
    config_value = config.CONFIG.Get(name)
  except (config_lib.Error, type_info.TypeValueError) as e:
    logging.exception("Can't get config value %s: %s", name, e)
    return config_pb2.ApiConfigOption(name=name, is_invalid=True)

  if config_value is not None:
    res.is_invalid = not _IsSupportedValueType(config_value)

    if res.is_invalid:
      return res

    if rdfvalue.RDFInteger.IsNumeric(config_value) and not isinstance(
        config_value, bool
    ):
      if isinstance(config_value, rdfvalue.RDFInteger) or isinstance(
          config_value, float
      ):
        config_value = int(config_value)
      res.type = config_pb2.Int64Value.__name__
      res.value.Pack(config_pb2.Int64Value(value=config_value))
    elif isinstance(config_value, rdfvalue.Duration):
      res.type = config_pb2.Int64Value.__name__
      res.value.Pack(config_pb2.Int64Value(value=config_value.microseconds))
    elif isinstance(config_value, rdfvalue.RDFString):
      res.type = config_pb2.StringValue.__name__
      res.value.Pack(config_pb2.StringValue(value=str(config_value)))
    elif isinstance(config_value, str):
      res.type = config_pb2.StringValue.__name__
      res.value.Pack(config_pb2.StringValue(value=config_value))
    elif isinstance(config_value, rdfvalue.RDFBytes):
      res.type = config_pb2.BytesValue.__name__
      res.value.Pack(config_pb2.BytesValue(value=config_value.AsBytes()))
    elif isinstance(config_value, bytes):
      res.type = config_pb2.BytesValue.__name__
      res.value.Pack(config_pb2.BytesValue(value=config_value))
    elif isinstance(config_value, bool):
      res.type = config_pb2.BoolValue.__name__
      res.value.Pack(config_pb2.BoolValue(value=config_value))
    if isinstance(config_value, rdf_structs.EnumNamedValue):
      res.type = config_pb2.StringValue.__name__
      res.value.Pack(config_pb2.StringValue(value=str(config_value)))
    if isinstance(config_value, rdf_structs.RDFProtoStruct):
      res.type = config_value.__class__.__name__
      res.value.Pack(config_value.AsPrimitiveProto())

  return res


class ApiGetConfigHandler(api_call_handler_base.ApiCallHandler):
  """Renders GRR's server configuration."""

  proto_result_type = config_pb2.ApiGetConfigResult

  def _ListParametersInSection(self, section):
    for descriptor in sorted(config.CONFIG.type_infos, key=lambda x: x.name):
      if descriptor.section == section:
        yield descriptor.name

  def Handle(self, unused_args, context=None):
    """Build the data structure representing the config."""

    sections = {}
    for descriptor in config.CONFIG.type_infos:
      if descriptor.section in sections:
        continue

      section_data = {}
      for parameter in self._ListParametersInSection(descriptor.section):
        section_data[parameter] = ApiConfigOptionFromOptionName(parameter)

      sections[descriptor.section] = section_data

    result = config_pb2.ApiGetConfigResult()
    for section_name in sorted(sections):
      section = sections[section_name]

      api_section = config_pb2.ApiConfigSection(name=section_name)
      # TODO: Replace with `clear()` once upgraded.
      del api_section.options[:]
      for param_name in sorted(section):
        api_section.options.append(section[param_name])
      result.sections.append(api_section)

    return result


class ApiGetConfigOptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders single option from a GRR server's configuration."""

  proto_args_type = config_pb2.ApiGetConfigOptionArgs
  proto_result_type = config_pb2.ApiConfigOption

  def Handle(
      self,
      args: config_pb2.ApiGetConfigOptionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> config_pb2.ApiConfigOption:
    """Renders specified config option."""

    if not args.name:
      raise ValueError("Name not specified.")

    return ApiConfigOptionFromOptionName(args.name)


def _GetSignedBlobsRoots() -> (
    dict[config_pb2.ApiGrrBinary.Type, rdfvalue.RDFURN]
):
  return {
      config_pb2.ApiGrrBinary.Type.PYTHON_HACK: (
          signed_binary_utils.GetAFF4PythonHackRoot()
      ),
      config_pb2.ApiGrrBinary.Type.EXECUTABLE: (
          signed_binary_utils.GetAFF4ExecutablesRoot()
      ),
  }


def _GetSignedBinaryMetadata(
    binary_type: config_pb2.ApiGrrBinary.Type, relative_path: str
) -> config_pb2.ApiGrrBinary:
  """Fetches metadata for the given binary from the datastore.

  Args:
    binary_type: ApiGrrBinary.Type of the binary.
    relative_path: Relative path of the binary, relative to the canonical URN
      roots for signed binaries (see _GetSignedBlobsRoots()).

  Returns:
    An ApiGrrBinary containing metadata for the binary.
  """
  root_urn = _GetSignedBlobsRoots()[binary_type]
  binary_urn = root_urn.Add(relative_path)
  blob_iterator, timestamp = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
      binary_urn
  )
  binary_size = 0
  has_valid_signature = True
  for blob in blob_iterator:
    binary_size += len(blob.data)
    if not has_valid_signature:
      # No need to check the signature if a previous blob had an invalid
      # signature.
      continue
    try:
      blob.Verify(config.CONFIG["Client.executable_signing_public_key"])
    except rdf_crypto.Error:
      has_valid_signature = False

  return config_pb2.ApiGrrBinary(
      path=relative_path,
      type=binary_type,
      size=binary_size,
      timestamp=int(timestamp),
      has_valid_signature=has_valid_signature,
  )


class ApiListGrrBinariesHandler(api_call_handler_base.ApiCallHandler):
  """Renders a list of available GRR binaries."""

  proto_args_type = config_pb2.ApiListGrrBinariesArgs
  proto_result_type = config_pb2.ApiListGrrBinariesResult

  def _ListBinaries(
      self, include_metadata: bool
  ) -> list[config_pb2.ApiGrrBinary]:
    roots = _GetSignedBlobsRoots()
    binary_urns = signed_binary_utils.FetchURNsForAllSignedBinaries()
    api_binaries = []
    for binary_urn in sorted(binary_urns):
      for binary_type, root in roots.items():
        relative_path = binary_urn.RelativeName(root)
        if relative_path:
          if include_metadata:
            api_binary = _GetSignedBinaryMetadata(binary_type, relative_path)
            api_binaries.append(api_binary)
          else:
            api_binaries.append(
                config_pb2.ApiGrrBinary(
                    path=relative_path,
                    type=binary_type,
                )
            )
    return api_binaries

  def Handle(
      self,
      args: config_pb2.ApiListGrrBinariesArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> config_pb2.ApiListGrrBinariesResult:
    return config_pb2.ApiListGrrBinariesResult(
        items=self._ListBinaries(args.include_metadata)
    )


class ApiGetGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Fetches metadata for a given GRR binary."""

  proto_args_type = config_pb2.ApiGetGrrBinaryArgs
  proto_result_type = config_pb2.ApiGrrBinary

  def Handle(
      self,
      args: config_pb2.ApiGetGrrBinaryArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> config_pb2.ApiGrrBinary:
    return _GetSignedBinaryMetadata(
        binary_type=args.type, relative_path=args.path
    )


class ApiGetGrrBinaryBlobHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  proto_args_type = config_pb2.ApiGetGrrBinaryBlobArgs

  CHUNK_SIZE = 1024 * 1024 * 4

  def Handle(
      self,
      args: config_pb2.ApiGetGrrBinaryBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    root_urn = _GetSignedBlobsRoots()[args.type]
    binary_urn = root_urn.Add(args.path)
    binary_size = signed_binary_utils.FetchSizeOfSignedBinary(binary_urn)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn
    )
    chunk_iterator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=self.CHUNK_SIZE
    )
    return api_call_handler_base.ApiBinaryStream(
        filename=binary_urn.Basename(),
        content_generator=chunk_iterator,
        content_length=binary_size,
    )


class ApiGetUiConfigHandler(api_call_handler_base.ApiCallHandler):
  """Returns config values for AdminUI (e.g. heading name, help url)."""

  proto_result_type = config_pb2.ApiUiConfig

  def Handle(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> config_pb2.ApiUiConfig:
    del args, context  # Unused.

    default_hunt_runner_args = models_hunts.CreateHuntRunnerArgs()
    hunt_config = config.CONFIG["AdminUI.hunt_config"]
    if hunt_config:
      hunt_config = hunt_config.AsPrimitiveProto()

    if hunt_config and (
        hunt_config.default_include_labels or hunt_config.default_exclude_labels
    ):
      default_hunt_runner_args.client_rule_set.CopyFrom(
          jobs_pb2.ForemanClientRuleSet(
              match_mode=jobs_pb2.ForemanClientRuleSet.MatchMode.MATCH_ALL,
          )
      )
      if hunt_config.default_include_labels:
        default_hunt_runner_args.client_rule_set.rules.add().CopyFrom(
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                label=jobs_pb2.ForemanLabelClientRule(
                    match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.MATCH_ANY,
                    label_names=hunt_config.default_include_labels,
                ),
            )
        )
      if hunt_config.default_exclude_labels:
        default_hunt_runner_args.client_rule_set.rules.add().CopyFrom(
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.LABEL,
                label=jobs_pb2.ForemanLabelClientRule(
                    match_mode=jobs_pb2.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
                    label_names=hunt_config.default_exclude_labels,
                ),
            )
        )
    default_output_plugins: list[output_plugin_pb2.OutputPluginDescriptor] = []
    output_plugins_config = config.CONFIG[
        "AdminUI.new_hunt_wizard.default_output_plugins"
    ]
    if output_plugins_config:
      for plugin in output_plugins_config.split(","):
        default_output_plugins.append(
            output_plugin_pb2.OutputPluginDescriptor(plugin_name=plugin.strip())
        )

    res = config_pb2.ApiUiConfig(
        heading=config.CONFIG["AdminUI.heading"],
        report_url=config.CONFIG["AdminUI.report_url"],
        help_url=config.CONFIG["AdminUI.help_url"],
        grr_version=config.CONFIG["Source.version_string"],
        profile_image_url=config.CONFIG["AdminUI.profile_image_url"],
        default_hunt_runner_args=default_hunt_runner_args,
        default_output_plugins=default_output_plugins,
        default_access_duration_seconds=config.CONFIG["ACL.token_expiry"],
        max_access_duration_seconds=config.CONFIG["ACL.token_max_expiry"],
    )

    if hunt_config:
      res.hunt_config.CopyFrom(hunt_config)

    client_warnings = config.CONFIG["AdminUI.client_warnings"]
    if client_warnings:
      res.client_warnings.CopyFrom(client_warnings.AsPrimitiveProto())

    return res
