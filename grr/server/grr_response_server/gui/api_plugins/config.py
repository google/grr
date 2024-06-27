#!/usr/bin/env python
"""API handlers for accessing config."""

import logging

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import config_pb2
from grr_response_server import foreman_rules
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_call_handler_base
from grr_response_server.rdfvalues import hunts as rdf_hunts

# TODO(user): sensitivity of config options and sections should
# probably be defined together with the options themselves. Keeping
# the list of redacted options and settings here may lead to scenario
# when new sensitive option is added, but these lists are not updated.
REDACTED_OPTIONS = [
    "AdminUI.django_secret_key",
    "AdminUI.csrf_secret_key",
    "BigQuery.service_acct_json",
    "Mysql.password",
    "Mysql.database_password",
    "Worker.smtp_password",
]
REDACTED_SECTIONS = ["PrivateKeys", "Users"]


def _IsSupportedValueType(value: any) -> bool:
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


class ApiConfigOption(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiConfigOption

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
      config_value = config.CONFIG.Get(name)
    except (config_lib.Error, type_info.TypeValueError) as e:
      logging.exception("Can't get config value %s: %s", name, e)
      self.is_invalid = True
      return self

    if config_value is not None:
      self.is_invalid = not _IsSupportedValueType(config_value)

      if self.is_invalid:
        return self

      if rdfvalue.RDFInteger.IsNumeric(config_value):
        self.type = rdfvalue.RDFInteger.__name__
        self.value = rdfvalue.RDFInteger(config_value)
      elif isinstance(config_value, str):
        self.type = rdfvalue.RDFString.__name__
        self.value = rdfvalue.RDFString(config_value)
      elif isinstance(config_value, bytes):
        self.type = rdfvalue.RDFBytes.__name__
        self.value = rdfvalue.RDFBytes(config_value)
      elif isinstance(config_value, bool):
        self.type = "bool"
        self.value = config_value
      elif isinstance(config_value, rdfvalue.RDFValue):
        self.type = config_value.__class__.__name__
        self.value = config_value

    return self


class ApiConfigSection(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiConfigSection
  rdf_deps = [
      ApiConfigOption,
  ]


class ApiGetConfigResult(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetConfigResult
  rdf_deps = [
      ApiConfigSection,
  ]


class ApiGetConfigHandler(api_call_handler_base.ApiCallHandler):
  """Renders GRR's server configuration."""

  result_type = ApiGetConfigResult

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
        section_data[parameter] = ApiConfigOption().InitFromConfigOption(
            parameter
        )

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
  protobuf = config_pb2.ApiGetConfigOptionArgs


class ApiGetConfigOptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders single option from a GRR server's configuration."""

  args_type = ApiGetConfigOptionArgs
  result_type = ApiConfigOption

  def Handle(self, args, context=None):
    """Renders specified config option."""

    if not args.name:
      raise ValueError("Name not specified.")

    return ApiConfigOption().InitFromConfigOption(args.name)


class ApiGrrBinary(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGrrBinary
  rdf_deps = [
      rdfvalue.ByteSize,
      rdfvalue.RDFDatetime,
  ]


class ApiListGrrBinariesResult(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiListGrrBinariesResult
  rdf_deps = [
      ApiGrrBinary,
  ]


def _GetSignedBlobsRoots():
  return {
      ApiGrrBinary.Type.PYTHON_HACK: (
          signed_binary_utils.GetAFF4PythonHackRoot()
      ),
      ApiGrrBinary.Type.EXECUTABLE: (
          signed_binary_utils.GetAFF4ExecutablesRoot()
      ),
  }


def _GetSignedBinaryMetadata(binary_type, relative_path):
  """Fetches metadata for the given binary from the datastore.

  Args:
    binary_type: ApiGrrBinary.Type of the binary.
    relative_path: Relative path of the binary, relative to the canonical URN
      roots for signed binaries (see _GetSignedBlobsRoots()).

  Returns:
    An ApiGrrBinary RDFProtoStruct containing metadata for the binary.
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

  return ApiGrrBinary(
      path=relative_path,
      type=binary_type,
      size=binary_size,
      timestamp=timestamp,
      has_valid_signature=has_valid_signature,
  )


class ApiListGrrBinariesHandler(api_call_handler_base.ApiCallHandler):
  """Renders a list of available GRR binaries."""

  result_type = ApiListGrrBinariesResult

  def _ListSignedBlobs(self, context=None):
    roots = _GetSignedBlobsRoots()
    binary_urns = signed_binary_utils.FetchURNsForAllSignedBinaries()
    api_binaries = []
    for binary_urn in sorted(binary_urns):
      for binary_type, root in roots.items():
        relative_path = binary_urn.RelativeName(root)
        if relative_path:
          api_binary = _GetSignedBinaryMetadata(binary_type, relative_path)
          api_binaries.append(api_binary)
    return api_binaries

  def Handle(self, unused_args, context=None):
    return ApiListGrrBinariesResult(
        items=self._ListSignedBlobs(context=context)
    )


class ApiGetGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryArgs


class ApiGetGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Fetches metadata for a given GRR binary."""

  args_type = ApiGetGrrBinaryArgs
  result_type = ApiGrrBinary

  def Handle(self, args, context=None):
    return _GetSignedBinaryMetadata(
        binary_type=args.type, relative_path=args.path
    )


class ApiGetGrrBinaryBlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryBlobArgs


class ApiGetGrrBinaryBlobHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  args_type = ApiGetGrrBinaryBlobArgs

  CHUNK_SIZE = 1024 * 1024 * 4

  def Handle(self, args, context=None):
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


class ApiUiConfig(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiUiConfig
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
      rdf_config.AdminUIClientWarningsConfigOption,
      rdf_config.AdminUIHuntConfig,
  ]


class ApiGetUiConfigHandler(api_call_handler_base.ApiCallHandler):
  """Returns config values for AdminUI (e.g. heading name, help url)."""

  result_type = ApiUiConfig

  def Handle(self, args, context=None):
    del args, context  # Unused.

    default_hunt_runner_args = rdf_hunts.HuntRunnerArgs()
    hunt_config = config.CONFIG["AdminUI.hunt_config"]
    if hunt_config and (
        hunt_config.default_include_labels or hunt_config.default_exclude_labels
    ):
      default_hunt_runner_args.client_rule_set = (
          foreman_rules.ForemanClientRuleSet(
              match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
          )
      )
      if hunt_config.default_include_labels:
        default_hunt_runner_args.client_rule_set.rules.append(
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.LABEL,
                label=foreman_rules.ForemanLabelClientRule(
                    match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
                    label_names=hunt_config.default_include_labels,
                ),
            )
        )
      if hunt_config.default_exclude_labels:
        default_hunt_runner_args.client_rule_set.rules.append(
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.LABEL,
                label=foreman_rules.ForemanLabelClientRule(
                    match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
                    label_names=hunt_config.default_exclude_labels,
                ),
            )
        )

    return ApiUiConfig(
        heading=config.CONFIG["AdminUI.heading"],
        report_url=config.CONFIG["AdminUI.report_url"],
        help_url=config.CONFIG["AdminUI.help_url"],
        grr_version=config.CONFIG["Source.version_string"],
        profile_image_url=config.CONFIG["AdminUI.profile_image_url"],
        default_hunt_runner_args=default_hunt_runner_args,
        hunt_config=config.CONFIG["AdminUI.hunt_config"],
        client_warnings=config.CONFIG["AdminUI.client_warnings"],
        default_access_duration_seconds=config.CONFIG["ACL.token_expiry"],
        max_access_duration_seconds=config.CONFIG["ACL.token_max_expiry"],
    )
