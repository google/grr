#!/usr/bin/env python
"""The base class for ApiCallHandlers."""

from grr.lib import registry


class Error(Exception):
  pass


class ResourceNotFoundError(Error):
  """Raised when a resource could not be found."""


class ApiBinaryStream(object):
  """Object to be returned from streaming API methods."""

  def __init__(self, filename, content_generator=None):
    """ApiBinaryStream constructor.

    Args:
      filename: A file name to be used by the browser when user downloads the
          file.
      content_generator: A generator that yields byte chunks (of any size) to
          be streamed to the user.

    Raises:
      ValueError: if content_generator is None.
    """
    self.filename = filename

    if content_generator is None:
      raise ValueError("content_generator can't be None")
    self.content_generator = content_generator

  def GenerateContent(self):
    """Generates content of the stream.

    Yields:
      Byte chunks (of any size) to be streamed to the user.
    """

    for chunk in self.content_generator:
      yield chunk


class ApiCallHandler(object):
  """Baseclass for restful API renderers."""

  __metaclass__ = registry.MetaclassRegistry

  # Identifies what this renderer is about. Category is an arbitrary string
  # used by documentation rendering to group renderers together. Possible
  # categories are: "Hunts", "Flows", "Configuration", etc.
  category = None

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

  # RDFValue type returned by the handler. This is only used by new handlers
  # that implement Handle() method. Legacy handlers don't have Handle()
  # implemented and return arbitrary data structures from Render() method.
  result_type = None

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

  # enabled_by_default=True means renderers are accessible by authenticated
  # users by default. Set this to False to disable a renderer and grant explicit
  # ACL'ed access in API.RendererACLFile.
  enabled_by_default = True

  # If True, when converting response to JSON, strip type information from root
  # fields of the resulting proto.
  strip_json_root_fields_types = True

  # NOTE: Render() is deprecated in favor of Handle(). Main difference of
  # Render() and Handle() is that Handle() returns an RDFValue, while Render()
  # return arbitrary data structures.
  def Render(self, args, token=None):
    """Renders response as a plain python object."""
    raise NotImplementedError()

  def Handle(self, args, token=None):
    """Handles request and returns an RDFValue of result_type."""
    raise NotImplementedError()
