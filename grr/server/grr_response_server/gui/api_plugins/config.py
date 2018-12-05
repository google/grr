#!/usr/bin/env python
"""API handlers for accessing config."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import config_lib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import config_pb2
from grr_response_server import signed_binary_utils
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils

# TODO(user): sensitivity of config options and sections should
# probably be defined together with the options themselves. Keeping
# the list of redacted options and settings here may lead to scenario
# when new sensitive option is added, but these lists are not updated.
REDACTED_OPTIONS = [
    "AdminUI.django_secret_key", "AdminUI.csrf_secret_key",
    "BigQuery.service_acct_json", "Mysql.database_password",
    "Worker.smtp_password"
]
REDACTED_SECTIONS = ["PrivateKeys", "Users"]


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

  def Handle(self, unused_args, token=None):
    """Build the data structure representing the config."""

    sections = {}
    for descriptor in config.CONFIG.type_infos:
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
  protobuf = config_pb2.ApiGetConfigOptionArgs


class ApiGetConfigOptionHandler(api_call_handler_base.ApiCallHandler):
  """Renders single option from a GRR server's configuration."""

  args_type = ApiGetConfigOptionArgs
  result_type = ApiConfigOption

  def Handle(self, args, token=None):
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
      ApiGrrBinary.Type.PYTHON_HACK:
          signed_binary_utils.GetAFF4PythonHackRoot(),
      ApiGrrBinary.Type.EXECUTABLE:
          signed_binary_utils.GetAFF4ExecutablesRoot()
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
  blob_iterator, timestamp = signed_binary_utils.FetchBlobsForSignedBinary(
      binary_urn)
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
      has_valid_signature=has_valid_signature)


class ApiListGrrBinariesHandler(api_call_handler_base.ApiCallHandler):
  """Renders a list of available GRR binaries."""

  result_type = ApiListGrrBinariesResult

  def _ListSignedBlobs(self, token=None):
    roots = _GetSignedBlobsRoots()
    binary_urns = signed_binary_utils.FetchURNsForAllSignedBinaries(token=token)
    api_binaries = []
    for binary_urn in sorted(binary_urns):
      for binary_type, root in iteritems(roots):
        relative_path = binary_urn.RelativeName(root)
        if relative_path:
          api_binary = _GetSignedBinaryMetadata(binary_type, relative_path)
          api_binaries.append(api_binary)
    return api_binaries

  def Handle(self, unused_args, token=None):
    return ApiListGrrBinariesResult(items=self._ListSignedBlobs(token=token))


class ApiGetGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryArgs


class ApiGetGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Fetches metadata for a given GRR binary."""

  args_type = ApiGetGrrBinaryArgs
  result_type = ApiGrrBinary

  def Handle(self, args, token=None):
    return _GetSignedBinaryMetadata(
        binary_type=args.type, relative_path=args.path)


class ApiGetGrrBinaryBlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryBlobArgs


class ApiGetGrrBinaryBlobHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  args_type = ApiGetGrrBinaryBlobArgs

  CHUNK_SIZE = 1024 * 1024 * 4

  def Handle(self, args, token=None):
    root_urn = _GetSignedBlobsRoots()[args.type]
    binary_urn = root_urn.Add(args.path)
    binary_size = signed_binary_utils.FetchSizeOfSignedBinary(
        binary_urn, token=token)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinary(
        binary_urn, token=token)
    chunk_iterator = signed_binary_utils.StreamSignedBinaryContents(
        blob_iterator, chunk_size=self.CHUNK_SIZE)
    return api_call_handler_base.ApiBinaryStream(
        filename=binary_urn.Basename(),
        content_generator=chunk_iterator,
        content_length=binary_size)
