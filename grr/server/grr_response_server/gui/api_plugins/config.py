#!/usr/bin/env python
"""API handlers for accessing config."""

import logging

from grr import config
from grr.lib import config_lib

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import config_pb2
from grr.server.grr_response_server import aff4

from grr.server.grr_response_server.aff4_objects import collects as aff4_collects

from grr.server.grr_response_server.gui import api_call_handler_base

from grr.server.grr_response_server.gui import api_call_handler_utils

# TODO(user): sensitivity of config options and sections should
# probably be defined together with the options themselves. Keeping
# the list of redacted options and settings here may lead to scenario
# when new sensitive option is added, but these lists are not updated.
REDACTED_OPTIONS = [
    "AdminUI.django_secret_key", "AdminUI.csrf_secret_key",
    "Mysql.database_password", "Worker.smtp_password"
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
      ApiGrrBinary.Type.PYTHON_HACK: aff4.FACTORY.GetPythonHackRoot(),
      ApiGrrBinary.Type.EXECUTABLE: aff4.FACTORY.GetExecutablesRoot()
  }


def _ValidateSignedBlobSignature(fd):
  public_key = config.CONFIG["Client.executable_signing_public_key"]

  for blob in fd:
    try:
      blob.Verify(public_key)
    except rdf_crypto.Error:
      return False

  return True


class ApiListGrrBinariesHandler(api_call_handler_base.ApiCallHandler):
  """Renders a list of available GRR binaries."""

  result_type = ApiListGrrBinariesResult

  def _ListSignedBlobs(self, token=None):
    roots = _GetSignedBlobsRoots()

    binary_urns = []
    for _, children in aff4.FACTORY.RecursiveMultiListChildren(roots.values()):
      binary_urns.extend(children)

    binary_fds = list(
        aff4.FACTORY.MultiOpen(
            binary_urns,
            aff4_type=aff4_collects.GRRSignedBlob,
            mode="r",
            token=token))

    items = []
    for fd in sorted(binary_fds, key=lambda f: f.urn):
      for binary_type, root in roots.items():
        rel_name = fd.urn.RelativeName(root)
        if rel_name:
          api_binary = ApiGrrBinary(
              path=rel_name,
              type=binary_type,
              size=fd.size,
              timestamp=fd.Get(fd.Schema.TYPE).age,
              has_valid_signature=_ValidateSignedBlobSignature(fd))
          items.append(api_binary)

    return items

  def Handle(self, unused_args, token=None):
    return ApiListGrrBinariesResult(items=self._ListSignedBlobs(token=token))


class ApiGetGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryArgs


class ApiGetGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  args_type = ApiGetGrrBinaryArgs
  result_type = ApiGrrBinary

  def Handle(self, args, token=None):
    root_urn = _GetSignedBlobsRoots()[args.type]
    urn = root_urn.Add(args.path)

    fd = aff4.FACTORY.Open(
        urn, aff4_type=aff4_collects.GRRSignedBlob, token=token)
    return ApiGrrBinary(
        path=args.path,
        type=args.type,
        size=fd.size,
        timestamp=fd.Get(fd.Schema.TYPE).age,
        has_valid_signature=_ValidateSignedBlobSignature(fd))


class ApiGetGrrBinaryBlobArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryBlobArgs


class ApiGetGrrBinaryBlobHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  args_type = ApiGetGrrBinaryBlobArgs

  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateStreamContent(self, aff4_stream, cipher=None):
    while True:
      chunk = aff4_stream.Read(self.CHUNK_SIZE)
      if not chunk:
        break
      if not cipher:
        yield chunk
      else:
        yield cipher.Decrypt(chunk)

  def Handle(self, args, token=None):
    root_urn = _GetSignedBlobsRoots()[args.type]
    binary_urn = root_urn.Add(args.path)

    file_obj = aff4.FACTORY.Open(
        binary_urn, aff4_type=aff4.AFF4Stream, token=token)
    return api_call_handler_base.ApiBinaryStream(
        filename=file_obj.urn.Basename(),
        content_generator=self._GenerateStreamContent(file_obj),
        content_length=file_obj.size)
