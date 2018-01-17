#!/usr/bin/env python
"""API handlers for accessing config."""

import itertools

from grr import config
from grr.gui import api_call_handler_base

from grr.gui import api_call_handler_utils
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import structs as rdf_structs

from grr_response_proto.api import config_pb2

from grr.server import aff4

from grr.server.aff4_objects import collects as aff4_collects

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


class ApiListGrrBinariesHandler(api_call_handler_base.ApiCallHandler):
  """Renders a list of available GRR binaries."""

  result_type = ApiListGrrBinariesResult

  def _GetBinarySize(self, fd, components_blobs_map):
    if isinstance(fd, aff4_collects.ComponentObject):
      try:
        blob_fd = components_blobs_map[fd.blob_urn]
      except KeyError:
        return 0
      return blob_fd.size
    else:
      return fd.size

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
              timestamp=fd.Get(fd.Schema.TYPE).age)
          items.append(api_binary)

    return items

  def _ListComponents(self, token=None):
    components_urns = aff4.FACTORY.ListChildren(
        aff4.FACTORY.GetComponentSummariesRoot())

    blobs_root_urns = []
    components_fds = aff4.FACTORY.MultiOpen(
        components_urns, aff4_type=aff4_collects.ComponentObject, token=token)
    components_by_seed = {}
    for fd in components_fds:
      desc = fd.Get(fd.Schema.COMPONENT)
      if not desc:
        continue

      components_by_seed[desc.seed] = fd
      blobs_root_urns.append(aff4.FACTORY.GetComponentRoot().Add(desc.seed))

    blobs_urns = []
    for _, children in aff4.FACTORY.MultiListChildren(blobs_root_urns):
      blobs_urns.extend(children)
    blobs_fds = aff4.FACTORY.MultiOpen(
        blobs_urns, aff4_type=aff4.AFF4Stream, token=token)

    items = []
    for fd in sorted(blobs_fds, key=lambda f: f.urn):
      seed = fd.urn.Split()[-2]
      component_fd = components_by_seed[seed]

      items.append(
          ApiGrrBinary(
              path="%s/%s" %
              (component_fd.urn.Basename(),
               fd.urn.RelativeName(aff4.FACTORY.GetComponentRoot())),
              type=ApiGrrBinary.Type.COMPONENT,
              size=fd.size,
              timestamp=fd.Get(fd.Schema.TYPE).age))

    return items

  def Handle(self, unused_args, token=None):
    return ApiListGrrBinariesResult(items=itertools.chain(
        self._ListSignedBlobs(token=token), self._ListComponents(token=token)))


class ApiGetGrrBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = config_pb2.ApiGetGrrBinaryArgs


class ApiGetGrrBinaryHandler(api_call_handler_base.ApiCallHandler):
  """Streams a given GRR binary."""

  args_type = ApiGetGrrBinaryArgs

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
    if args.type == ApiGrrBinary.Type.COMPONENT:
      # First path component of the identifies the component summary, the
      # rest identifies the data blob.
      path_components = args.path.split("/")
      binary_urn = aff4.FACTORY.GetComponentRoot().Add("/".join(
          path_components[1:]))

      component_fd = aff4.FACTORY.Open(
          aff4.FACTORY.GetComponentSummariesRoot().Add(path_components[0]),
          aff4_type=aff4_collects.ComponentObject,
          token=token)
      summary = component_fd.Get(component_fd.Schema.COMPONENT)

      file_obj = aff4.FACTORY.Open(
          binary_urn, aff4_type=aff4.AFF4Stream, token=token)

      return api_call_handler_base.ApiBinaryStream(
          filename=component_fd.urn.Basename(),
          content_generator=self._GenerateStreamContent(
              file_obj, cipher=summary.cipher))
    else:
      root_urn = _GetSignedBlobsRoots()[args.type]
      binary_urn = root_urn.Add(args.path)

      file_obj = aff4.FACTORY.Open(
          binary_urn, aff4_type=aff4.AFF4Stream, token=token)
      return api_call_handler_base.ApiBinaryStream(
          filename=file_obj.urn.Basename(),
          content_generator=self._GenerateStreamContent(file_obj),
          content_length=file_obj.size)
