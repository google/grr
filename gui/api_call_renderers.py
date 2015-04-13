#!/usr/bin/env python
"""Renderers for API calls (that can be bound to HTTP API, for example)."""




from grr.lib import rdfvalue
from grr.lib import registry
from grr.proto import api_pb2


class Error(Exception):
  """Base class for API renderers exception."""


class ApiCallRendererNotFoundError(Error):
  """Raised when no renderer found for a given URL."""


class ApiCallAdditionalArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiCallAdditionalArgs

  def GetArgsClass(self):
    return rdfvalue.RDFValue.classes[self.type]


class ApiCallRenderer(object):
  """Baseclass for restful API renderers."""

  __metaclass__ = registry.MetaclassRegistry

  # RDFValue type used to handle API renderer arguments. This can be
  # a class object, an array of class objects or a function returning
  # either option.
  #
  # For GET renderers arguments will be passed via query parameters.
  # For POST renderers arguments will be passed via request payload.
  args_type = None

  # This is either a dictionary (key -> arguments class) of allowed additional
  # arguments types or a function returning this dictionary.
  #
  # addtional_args_types is only used when renderer's arguments RDFValue (
  # specified by args_type) has "additional_args" field of type
  # ApiCallAdditionalArgs.
  #
  # If this field is present, it will be filled with additional arguments
  # objects when the request is parsed. Keys of addtional_args_types
  # dictionary are used as prefixes when parsing the request.
  #
  # For example, if additional_args_types is
  # {"AFF4Object": ApiAFF4ObjectRendererArgs} and request has following key-
  # value pair set: "AFF4Object.limit_lists" -> 10, then
  # ApiAFF4ObjectRendererArgs(limit_lists=10) object will be created and put
  # into "additional_args" list of this renderer's arguments RDFValue.
  additional_args_types = {}

  # This is a maximum time in seconds the renderer is allowed to run. Renderers
  # exceeding this time are killed softly (i.e. the time is not a guaranteed
  # maximum, but will be used as a guide).
  max_execution_time = 60

  # privileged=True means that the renderer was designed to run in a privileged
  # context when no ACL checks are made. It means that this renderer makes
  # all the necessary ACL-related checks itself.
  #
  # NOTE: renderers with privileged=True have to be designed with extra caution
  # as they run without any ACL checks in place and can therefore cause the
  # system to be compromised.
  privileged = False

  def Render(self, args, token=None):
    raise NotImplementedError()


def HandleApiCall(renderer, args, token=None):
  """Handles API call to a given renderers with given args and token."""

  if not hasattr(renderer, "Render"):
    renderer = ApiCallRenderer.classes[renderer]

  if renderer.privileged:
    token = token.SetUID()

  return renderer.Render(args, token=token)
